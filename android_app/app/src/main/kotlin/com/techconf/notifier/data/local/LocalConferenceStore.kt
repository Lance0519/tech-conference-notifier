package com.techconf.notifier.data.local

import android.content.Context
import android.content.SharedPreferences
import com.techconf.notifier.data.model.AlertSettings
import com.techconf.notifier.data.model.Conference
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class LocalConferenceStore(private val context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    companion object {
        private const val PREFS_NAME = "tech_conf_prefs"
        private const val KEY_BASE_URL = "base_url"
        const val DEFAULT_BASE_URL = "standalone"
        private const val KEY_REMIND_7D = "remind_7d"
        private const val KEY_REMIND_3D = "remind_3d"
        private const val KEY_REMIND_1D = "remind_1d"
        private const val KEY_REMIND_0D = "remind_0d"
        private const val KEY_CFP_ALERTS = "cfp_alerts"
        private const val KEY_LOCAL_PH_ONLY = "local_ph_only"
        private const val KEY_SYNC_INTERVAL = "sync_interval_hours"
        private const val KEY_BOOKMARKS_JSON = "bookmarks_json"
        private const val CACHE_FILE_NAME = "conferences_cache.json"

        @Volatile
        private var instance: LocalConferenceStore? = null

        fun getInstance(context: Context): LocalConferenceStore {
            return instance ?: synchronized(this) {
                instance ?: LocalConferenceStore(context.applicationContext).also { instance = it }
            }
        }
    }

    // Configurable Backend Base URL
    fun getBaseUrl(): String {
        return prefs.getString(KEY_BASE_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
    }

    fun setBaseUrl(url: String) {
        val cleanUrl = url.trim().removeSuffix("/")
        prefs.edit().putString(KEY_BASE_URL, cleanUrl).apply()
    }

    // Alert Settings
    fun getAlertSettings(): AlertSettings {
        return AlertSettings(
            remind7d = prefs.getBoolean(KEY_REMIND_7D, true),
            remind3d = prefs.getBoolean(KEY_REMIND_3D, true),
            remind1d = prefs.getBoolean(KEY_REMIND_1D, true),
            remind0d = prefs.getBoolean(KEY_REMIND_0D, true),
            cfpAlerts = prefs.getBoolean(KEY_CFP_ALERTS, true),
            localPhOnly = prefs.getBoolean(KEY_LOCAL_PH_ONLY, false),
            syncIntervalHours = prefs.getInt(KEY_SYNC_INTERVAL, 12)
        )
    }

    fun saveAlertSettings(settings: AlertSettings) {
        prefs.edit()
            .putBoolean(KEY_REMIND_7D, settings.remind7d)
            .putBoolean(KEY_REMIND_3D, settings.remind3d)
            .putBoolean(KEY_REMIND_1D, settings.remind1d)
            .putBoolean(KEY_REMIND_0D, settings.remind0d)
            .putBoolean(KEY_CFP_ALERTS, settings.cfpAlerts)
            .putBoolean(KEY_LOCAL_PH_ONLY, settings.localPhOnly)
            .putInt(KEY_SYNC_INTERVAL, settings.syncIntervalHours)
            .apply()
    }

    // Offline Bookmarks
    fun getSavedBookmarks(): List<Conference> {
        val jsonStr = prefs.getString(KEY_BOOKMARKS_JSON, null) ?: return emptyList()
        return try {
            val array = JSONArray(jsonStr)
            val list = mutableListOf<Conference>()
            for (i in 0 until array.length()) {
                val item = array.getJSONObject(i)
                val conf = Conference.fromJson(item)
                conf.isBookmarked = true
                list.add(conf)
            }
            list
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun saveBookmarks(bookmarks: List<Conference>) {
        val array = JSONArray()
        bookmarks.forEach {
            it.isBookmarked = true
            array.put(it.toJson())
        }
        prefs.edit().putString(KEY_BOOKMARKS_JSON, array.toString()).apply()
    }

    fun toggleLocalBookmark(conference: Conference): Boolean {
        val current = getSavedBookmarks().toMutableList()
        val existingIndex = current.indexOfFirst { it.id == conference.id }
        val isNowSaved: Boolean
        if (existingIndex >= 0) {
            current.removeAt(existingIndex)
            isNowSaved = false
        } else {
            val toSave = conference.copy(isBookmarked = true)
            current.add(toSave)
            isNowSaved = true
        }
        saveBookmarks(current)
        return isNowSaved
    }

    fun isEventBookmarked(eventId: String): Boolean {
        val current = getSavedBookmarks()
        return current.any { it.id == eventId }
    }

    // Offline Conferences Cache
    fun cacheConferences(conferences: List<Conference>) {
        try {
            val file = File(context.filesDir, CACHE_FILE_NAME)
            val array = JSONArray()
            conferences.forEach { array.put(it.toJson()) }
            file.writeText(array.toString())
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun getPrepackagedSeedConferences(): List<Conference> {
        return try {
            val text = context.assets.open("seed_conferences.json").bufferedReader().use { it.readText() }
            val array = JSONArray(text)
            val list = mutableListOf<Conference>()
            val bookmarkedIds = getSavedBookmarks().map { it.id }.toSet()
            for (i in 0 until array.length()) {
                val conf = Conference.fromJson(array.getJSONObject(i))
                conf.isBookmarked = bookmarkedIds.contains(conf.id)
                list.add(conf)
            }
            list
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun getCachedConferences(): List<Conference> {
        try {
            val file = File(context.filesDir, CACHE_FILE_NAME)
            val text: String = if (file.exists()) {
                file.readText()
            } else {
                // Seed initial verified conferences from APK assets on first launch!
                try {
                    val seed = context.assets.open("seed_conferences.json").bufferedReader().use { it.readText() }
                    file.writeText(seed)
                    seed
                } catch (e: Exception) {
                    "[]"
                }
            }
            val array = JSONArray(text)
            val list = mutableListOf<Conference>()
            val bookmarkedIds = getSavedBookmarks().map { it.id }.toSet()
            for (i in 0 until array.length()) {
                val conf = Conference.fromJson(array.getJSONObject(i))
                conf.isBookmarked = bookmarkedIds.contains(conf.id)
                list.add(conf)
            }
            return list
        } catch (e: Exception) {
            return emptyList()
        }
    }
}
