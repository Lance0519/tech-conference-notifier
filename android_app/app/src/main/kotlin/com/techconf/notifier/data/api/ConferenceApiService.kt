package com.techconf.notifier.data.api

import android.content.Context
import android.util.Log
import com.techconf.notifier.data.engine.DirectOnlineDiscoveryEngine
import com.techconf.notifier.data.local.LocalConferenceStore
import com.techconf.notifier.data.model.CategorySummary
import com.techconf.notifier.data.model.Conference
import com.techconf.notifier.data.model.MANDATORY_CATEGORIES
import com.techconf.notifier.data.model.NotificationHistoryRecord
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

class ConferenceApiService(private val context: Context) {

    private val localStore = LocalConferenceStore.getInstance(context)

    var baseUrl: String
        get() = localStore.getBaseUrl()
        set(value) = localStore.setBaseUrl(value)

    companion object {
        private const val TAG = "ConferenceApiService"
        private const val CONNECT_TIMEOUT_MS = 8000
        private const val READ_TIMEOUT_MS = 12000

        @Volatile
        private var instance: ConferenceApiService? = null

        fun getInstance(context: Context): ConferenceApiService {
            return instance ?: synchronized(this) {
                instance ?: ConferenceApiService(context.applicationContext).also { instance = it }
            }
        }
    }

    /**
     * Fetch conferences with optional filters: category, format, country, search query, days lookahead.
     * Operates 100% independently over Wi-Fi without needing a PC server, while supporting
     * custom self-hosted backends if configured.
     */
    suspend fun getEvents(
        category: String? = null,
        format: String? = null,
        country: String? = null,
        search: String? = null,
        days: Int = 180
    ): Result<List<Conference>> = withContext(Dispatchers.IO) {
        val currentBase = baseUrl.trim()
        val isStandalone = currentBase.isEmpty() || currentBase.equals("standalone", ignoreCase = true)

        var list: List<Conference> = emptyList()

        // 1. Try custom backend if not in standalone mode
        if (!isStandalone) {
            try {
                val queryParams = mutableListOf<String>()
                queryParams.add("days=$days")
                category?.let { if (it.isNotBlank()) queryParams.add("category=${URLEncoder.encode(it, "UTF-8")}") }
                format?.let { if (it.isNotBlank()) queryParams.add("format=${URLEncoder.encode(it, "UTF-8")}") }
                country?.let { if (it.isNotBlank()) queryParams.add("country=${URLEncoder.encode(it, "UTF-8")}") }
                search?.let { if (it.isNotBlank()) queryParams.add("search=${URLEncoder.encode(it, "UTF-8")}") }

                val urlString = "$currentBase/api/events?${queryParams.joinToString("&")}"
                val responseString = executeGet(urlString)
                val json = JSONObject(responseString)
                val eventsArray = json.getJSONArray("events")
                val serverList = mutableListOf<Conference>()
                val bookmarkedIds = localStore.getSavedBookmarks().map { it.id }.toSet()

                for (i in 0 until eventsArray.length()) {
                    val conf = Conference.fromJson(eventsArray.getJSONObject(i))
                    if (bookmarkedIds.contains(conf.id)) {
                        conf.isBookmarked = true
                    }
                    serverList.add(conf)
                }

                localStore.cacheConferences(serverList)
                list = serverList
            } catch (e: Exception) {
                Log.w(TAG, "Custom backend failed: ${e.message}, falling back to Direct Wi-Fi Discovery...")
            }
        }

        // 2. Direct Online Discovery over Wi-Fi (Standalone Mode or Backend unreachable)
        if (list.isEmpty()) {
            try {
                val cached = localStore.getCachedConferences()
                if (cached.isEmpty()) {
                    // First launch: initialize with bundled seed conferences immediately
                    val seed = localStore.getPrepackagedSeedConferences()
                    if (seed.isNotEmpty()) {
                        localStore.cacheConferences(seed)
                        list = seed
                    }
                } else {
                    list = cached
                }

                // Probe direct open-source repositories over Wi-Fi
                val directEngine = DirectOnlineDiscoveryEngine(context)
                val liveConfs = directEngine.discoverLiveConferences()
                if (liveConfs.isNotEmpty()) {
                    list = liveConfs
                }
            } catch (e: Exception) {
                Log.w(TAG, "Direct discovery encountered network error, falling back to local cache: ${e.message}")
            }
        }

        // 3. Fallback to local cache if offline
        if (list.isEmpty()) {
            list = localStore.getCachedConferences()
            if (list.isEmpty()) {
                list = localStore.getPrepackagedSeedConferences()
            }
        }

        // 4. Apply client-side filters
        var filtered = list
        if (!category.isNullOrBlank()) {
            filtered = filtered.filter { it.category.equals(category, ignoreCase = true) }
        }
        if (!format.isNullOrBlank()) {
            filtered = filtered.filter { it.format.equals(format, ignoreCase = true) }
        }
        if (!country.isNullOrBlank()) {
            if (country.equals("philippines", ignoreCase = true)) {
                filtered = filtered.filter { it.isPhilippines }
            } else {
                filtered = filtered.filter { it.country.contains(country, ignoreCase = true) }
            }
        }
        if (!search.isNullOrBlank()) {
            val q = search.lowercase()
            filtered = filtered.filter {
                it.name.lowercase().contains(q) ||
                        it.locationStr.lowercase().contains(q) ||
                        it.category.lowercase().contains(q)
            }
        }

        val bookmarkedIds = localStore.getSavedBookmarks().map { it.id }.toSet()
        filtered.forEach { it.isBookmarked = bookmarkedIds.contains(it.id) }

        Result.success(filtered)
    }

    /**
     * Retrieve single conference details by ID.
     */
    suspend fun getEventDetail(eventId: String): Result<Conference> = withContext(Dispatchers.IO) {
        try {
            val urlString = "$baseUrl/api/events/$eventId"
            val responseString = executeGet(urlString)
            val json = JSONObject(responseString)
            val eventObj = json.getJSONObject("event")
            val conf = Conference.fromJson(eventObj)
            if (localStore.isEventBookmarked(eventId)) {
                conf.isBookmarked = true
            }
            Result.success(conf)
        } catch (e: Exception) {
            Log.e(TAG, "getEventDetail error: ${e.message}")
            // Check offline cache or bookmarks
            val localConf = localStore.getCachedConferences().firstOrNull { it.id == eventId }
                ?: localStore.getSavedBookmarks().firstOrNull { it.id == eventId }
            if (localConf != null) {
                Result.success(localConf)
            } else {
                Result.failure(e)
            }
        }
    }

    /**
     * Retrieve 16 IT/CS categories with event counts.
     */
    suspend fun getCategories(): Result<List<CategorySummary>> = withContext(Dispatchers.IO) {
        try {
            val urlString = "$baseUrl/api/categories"
            val responseString = executeGet(urlString)
            val json = JSONObject(responseString)
            val arr = json.getJSONArray("categories")
            val list = mutableListOf<CategorySummary>()
            for (i in 0 until arr.length()) {
                val item = arr.getJSONObject(i)
                list.add(
                    CategorySummary(
                        name = item.getString("name"),
                        count = item.optInt("count", 0)
                    )
                )
            }
            Result.success(list)
        } catch (e: Exception) {
            Log.w(TAG, "getCategories network failed, falling back to local counts: ${e.message}")
            val cached = localStore.getCachedConferences()
            val counts = mutableMapOf<String, Int>()
            MANDATORY_CATEGORIES.forEach { counts[it] = 0 }
            cached.forEach { conf ->
                if (counts.containsKey(conf.category)) {
                    counts[conf.category] = (counts[conf.category] ?: 0) + 1
                }
            }
            val summaries = MANDATORY_CATEGORIES.map {
                CategorySummary(name = it, count = counts[it] ?: 0)
            }
            Result.success(summaries)
        }
    }

    /**
     * Retrieve user bookmarks with offline fallback.
     */
    suspend fun getBookmarks(): Result<List<Conference>> = withContext(Dispatchers.IO) {
        try {
            val urlString = "$baseUrl/api/bookmarks"
            val responseString = executeGet(urlString)
            val json = JSONObject(responseString)
            val arr = json.getJSONArray("events")
            val serverList = mutableListOf<Conference>()
            for (i in 0 until arr.length()) {
                val conf = Conference.fromJson(arr.getJSONObject(i))
                conf.isBookmarked = true
                serverList.add(conf)
            }
            // Merge with local bookmarks
            val localList = localStore.getSavedBookmarks()
            val combinedMap = mutableMapOf<String, Conference>()
            localList.forEach { combinedMap[it.id] = it }
            serverList.forEach { combinedMap[it.id] = it }
            val merged = combinedMap.values.toList()
            localStore.saveBookmarks(merged)
            Result.success(merged)
        } catch (e: Exception) {
            Log.w(TAG, "getBookmarks network failed, using local offline bookmarks: ${e.message}")
            Result.success(localStore.getSavedBookmarks())
        }
    }

    /**
     * Toggle bookmark state for an event.
     */
    suspend fun toggleBookmark(conference: Conference): Result<Boolean> = withContext(Dispatchers.IO) {
        // Toggle locally first for instantaneous UI update and offline guarantee
        val isNowLocalSaved = localStore.toggleLocalBookmark(conference)
        try {
            val urlString = "$baseUrl/api/bookmarks/${conference.id}"
            executePost(urlString, "")
        } catch (e: Exception) {
            Log.w(TAG, "Server bookmark sync queued locally: ${e.message}")
        }
        Result.success(isNowLocalSaved)
    }

    /**
     * Trigger background discovery run. Runs direct Wi-Fi discovery in standalone mode.
     */
    suspend fun triggerSync(): Result<String> = withContext(Dispatchers.IO) {
        val currentBase = baseUrl.trim()
        val isStandalone = currentBase.isEmpty() || currentBase.equals("standalone", ignoreCase = true)

        if (!isStandalone) {
            try {
                val urlString = "$currentBase/api/sync"
                val response = executePost(urlString, "")
                val json = JSONObject(response)
                return@withContext Result.success(json.optString("message", "Discovery run completed"))
            } catch (e: Exception) {
                Log.w(TAG, "Backend sync failed: ${e.message}, falling back to Direct Wi-Fi discovery...")
            }
        }

        try {
            val directEngine = DirectOnlineDiscoveryEngine(context)
            val updated = directEngine.discoverLiveConferences()
            Result.success("Direct Wi-Fi discovery synced ${updated.size} conferences successfully")
        } catch (e: Exception) {
            Log.e(TAG, "triggerSync failed: ${e.message}")
            Result.failure(e)
        }
    }

    /**
     * Fetch recent notification records.
     */
    suspend fun getNotifications(): Result<List<NotificationHistoryRecord>> = withContext(Dispatchers.IO) {
        try {
            val urlString = "$baseUrl/api/notifications"
            val responseString = executeGet(urlString)
            val json = JSONObject(responseString)
            val arr = json.getJSONArray("notifications")
            val list = mutableListOf<NotificationHistoryRecord>()
            for (i in 0 until arr.length()) {
                val item = arr.getJSONObject(i)
                list.add(
                    NotificationHistoryRecord(
                        id = item.optInt("id", 0),
                        eventId = item.optString("event_id", ""),
                        triggerType = item.optString("trigger_type", "reminder"),
                        channel = item.optString("channel", "mobile_push"),
                        sentAt = item.optString("sent_at", ""),
                        status = item.optString("status", "sent")
                    )
                )
            }
            Result.success(list)
        } catch (e: Exception) {
            Log.w(TAG, "getNotifications network failed: ${e.message}")
            Result.failure(e)
        }
    }

    // HTTP Helper GET
    private fun executeGet(urlString: String): String {
        val url = URL(urlString)
        val conn = url.openConnection() as HttpURLConnection
        conn.requestMethod = "GET"
        conn.connectTimeout = CONNECT_TIMEOUT_MS
        conn.readTimeout = READ_TIMEOUT_MS
        conn.setRequestProperty("Accept", "application/json")
        conn.setRequestProperty("User-Agent", "TechConfNotifier-Android/1.0")

        val responseCode = conn.responseCode
        if (responseCode in 200..299) {
            return conn.inputStream.bufferedReader().use(BufferedReader::readText)
        } else {
            val errorText = conn.errorStream?.bufferedReader()?.use(BufferedReader::readText) ?: ""
            throw RuntimeException("HTTP $responseCode: $errorText")
        }
    }

    // HTTP Helper POST
    private fun executePost(urlString: String, payload: String): String {
        val url = URL(urlString)
        val conn = url.openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.connectTimeout = CONNECT_TIMEOUT_MS
        conn.readTimeout = READ_TIMEOUT_MS
        conn.setRequestProperty("Content-Type", "application/json")
        conn.setRequestProperty("Accept", "application/json")
        conn.setRequestProperty("User-Agent", "TechConfNotifier-Android/1.0")
        conn.doOutput = true

        if (payload.isNotEmpty()) {
            conn.outputStream.bufferedWriter().use { it.write(payload) }
        }

        val responseCode = conn.responseCode
        if (responseCode in 200..299) {
            return conn.inputStream.bufferedReader().use(BufferedReader::readText)
        } else {
            val errorText = conn.errorStream?.bufferedReader()?.use(BufferedReader::readText) ?: ""
            throw RuntimeException("HTTP $responseCode: $errorText")
        }
    }
}
