package com.techconf.notifier.data.engine

import android.content.Context
import android.util.Log
import com.techconf.notifier.data.local.LocalConferenceStore
import com.techconf.notifier.data.model.Conference
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class DirectOnlineDiscoveryEngine(private val context: Context) {

    private val localStore = LocalConferenceStore.getInstance(context)

    companion object {
        private const val TAG = "DirectDiscoveryEngine"
        private const val BASE_FEED_URL = "https://raw.githubusercontent.com/tech-conferences/conference-data/main/conferences/%d/%s.json"

        // Open-source conference topics mapped to our 16 mandatory IT/CS categories
        private val TOPICS_MAP = mapOf(
            "general" to "Information Technology",
            "security" to "Cybersecurity",
            "devops" to "Cloud Computing and DevOps",
            "data" to "Data Science and Analytics",
            "python" to "Software Engineering",
            "javascript" to "Web and Mobile Development",
            "android" to "Web and Mobile Development",
            "ios" to "Web and Mobile Development",
            "mobile" to "Web and Mobile Development",
            "golang" to "Software Engineering",
            "rust" to "Software Engineering",
            "iot" to "Robotics and Internet of Things",
            "networking" to "Networking and Telecommunications",
            "leadership" to "Technology Entrepreneurship and Innovation"
        )
    }

    /**
     * Executes direct online discovery over Wi-Fi / cellular.
     * Fetches public JSON feeds, normalizes, deduplicates, merges with seed/cached events,
     * and returns the comprehensive list of conferences.
     */
    suspend fun discoverLiveConferences(): List<Conference> = withContext(Dispatchers.IO) {
        val currentYear = Calendar.getInstance().get(Calendar.YEAR)
        val yearsToFetch = listOf(currentYear, currentYear + 1)
        val discoveredConfs = mutableListOf<Conference>()

        // 1. Fetch from direct open-source repositories over Wi-Fi
        for (year in yearsToFetch) {
            for ((topic, category) in TOPICS_MAP) {
                try {
                    val feedUrl = String.format(Locale.US, BASE_FEED_URL, year, topic)
                    val jsonStr = downloadUrl(feedUrl) ?: continue
                    val array = JSONArray(jsonStr)
                    for (i in 0 until array.length()) {
                        val item = array.getJSONObject(i)
                        val conf = parseItemToConference(item, category, topic)
                        if (conf != null) {
                            discoveredConfs.add(conf)
                        }
                    }
                } catch (e: Exception) {
                    // Skip individual feed failures silently
                }
            }
        }

        // 2. Load existing/seed conferences (so Philippine conferences are never lost)
        val baseConfs = localStore.getCachedConferences().toMutableList()
        if (baseConfs.isEmpty()) {
            baseConfs.addAll(localStore.getPrepackagedSeedConferences())
        }

        // 3. Deduplicate and merge: seed/local conferences take precedence
        val mergedMap = LinkedHashMap<String, Conference>()

        // Put base conferences first (prioritizing Philippine & verified events)
        for (c in baseConfs) {
            val key = normalizeEventKey(c.name, c.startDate)
            mergedMap[key] = c
        }

        // Merge newly discovered conferences if not already present
        for (c in discoveredConfs) {
            val key = normalizeEventKey(c.name, c.startDate)
            if (!mergedMap.containsKey(key)) {
                mergedMap[key] = c
            }
        }

        // 4. Update countdown days and date metadata based on current device time
        val updatedList = mergedMap.values.map { updateConferenceTiming(it) }.sortedWith(
            compareBy<Conference> { if (it.isPhilippines) 0 else 1 }
                .thenBy { it.startDate }
        )

        // 5. Persist to local cache for offline reading
        localStore.cacheConferences(updatedList)
        Log.i(TAG, "Direct discovery completed: ${updatedList.size} upcoming conferences active.")

        updatedList
    }

    private fun parseItemToConference(item: JSONObject, defaultCategory: String, topic: String): Conference? {
        val name = item.optString("name", "").trim()
        val startDate = item.optString("startDate", "").trim()
        val url = item.optString("url", "").trim()
        if (name.isEmpty() || startDate.isEmpty() || url.isEmpty()) return null

        val endDate = if (item.has("endDate")) item.optString("endDate") else startDate
        val city = item.optString("city", "").trim()
        val country = item.optString("country", "").trim()
        val online = item.optBoolean("online", false)
        val cfpUrl = if (item.has("cfpUrl")) item.optString("cfpUrl") else null
        val cfpEndDate = if (item.has("cfpEndDate")) item.optString("cfpEndDate") else null

        val isPh = country.contains("Philippines", ignoreCase = true) ||
                city.contains("Manila", ignoreCase = true) ||
                city.contains("Cebu", ignoreCase = true) ||
                city.contains("Davao", ignoreCase = true)

        val format = when {
            online && (city.isNotEmpty() || country.isNotEmpty()) -> "hybrid"
            online -> "virtual"
            else -> "in_person"
        }

        val geoTier = if (isPh) "local_ph" else "international"
        val locStr = when {
            isPh -> "🇵🇭 $city, Philippines"
            format == "virtual" -> "Online / Virtual"
            city.isNotEmpty() && country.isNotEmpty() -> "$city, $country"
            country.isNotEmpty() -> country
            else -> "International"
        }

        val id = generateClusterId(name, startDate)

        return Conference(
            id = id,
            name = name,
            category = defaultCategory,
            source = "direct_wifi_feed",
            startDate = startDate,
            endDate = endDate,
            url = url,
            city = if (city.isEmpty()) "Not announced" else city,
            country = if (country.isEmpty()) "Not announced" else country,
            location = locStr,
            locationStr = locStr,
            format = format,
            isOnline = format in listOf("virtual", "hybrid"),
            isPhilippines = isPh,
            geographicTier = geoTier,
            cfpUrl = cfpUrl,
            cfpDeadline = cfpEndDate,
            hasCfpOpen = !cfpEndDate.isNullOrBlank(),
            verificationStatus = "verified",
            status = "scheduled"
        )
    }

    private fun updateConferenceTiming(conf: Conference): Conference {
        val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("Asia/Manila")
        val now = Calendar.getInstance()
        now.set(Calendar.HOUR_OF_DAY, 0)
        now.set(Calendar.MINUTE, 0)
        now.set(Calendar.SECOND, 0)
        now.set(Calendar.MILLISECOND, 0)

        val confStart = try {
            sdf.parse(conf.startDate)
        } catch (e: Exception) {
            null
        }

        val daysUntil = if (confStart != null) {
            val diffMs = confStart.time - now.timeInMillis
            (diffMs / (1000 * 60 * 60 * 24)).toInt()
        } else {
            conf.daysUntil
        }

        val statusLabel = when {
            daysUntil < 0 -> "Completed"
            daysUntil == 0 -> "Starts TODAY!"
            daysUntil == 1 -> "Starts TOMORROW!"
            daysUntil in 2..7 -> "Starts in $daysUntil days (This Week)"
            daysUntil in 8..14 -> "Starts in $daysUntil days (Next Week)"
            daysUntil in 15..30 -> "Starts in $daysUntil days (~1 month)"
            else -> "Starts in $daysUntil days"
        }

        return conf.copy(
            daysUntil = daysUntil,
            statusLabel = statusLabel
        )
    }

    private fun normalizeEventKey(name: String, startDate: String): String {
        val cleanName = name.lowercase().replace(Regex("[^a-z0-9]"), "")
        return "${cleanName}_$startDate"
    }

    private fun generateClusterId(name: String, startDate: String): String {
        val key = "${name.lowercase()}_$startDate"
        return Integer.toHexString(key.hashCode())
    }

    private fun downloadUrl(urlString: String): String? {
        var conn: HttpURLConnection? = null
        return try {
            val url = URL(urlString)
            conn = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 8000
                readTimeout = 10000
                requestMethod = "GET"
                setRequestProperty("User-Agent", "TechConfNotifier-Android/1.0")
            }
            if (conn.responseCode == 200) {
                BufferedReader(InputStreamReader(conn.inputStream, "UTF-8")).use {
                    it.readText()
                }
            } else {
                null
            }
        } catch (e: Exception) {
            null
        } finally {
            conn?.disconnect()
        }
    }
}
