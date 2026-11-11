package com.techconf.notifier.worker

import android.content.Context
import android.util.Log
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.techconf.notifier.data.api.ConferenceApiService
import com.techconf.notifier.data.local.LocalConferenceStore
import java.util.concurrent.TimeUnit

class EventSyncWorker(
    private val context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    companion object {
        const val WORK_NAME = "tech_conf_periodic_sync"
        private const val TAG = "EventSyncWorker"

        /**
         * Enqueue periodic background sync using WorkManager (default: every 12 hours).
         */
        fun schedulePeriodicSync(context: Context, intervalHours: Long = 12) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val periodicRequest = PeriodicWorkRequestBuilder<EventSyncWorker>(
                intervalHours,
                TimeUnit.HOURS,
                30,
                TimeUnit.MINUTES // Flex window
            )
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.UPDATE,
                periodicRequest
            )
            Log.i(TAG, "Periodic EventSyncWorker scheduled every $intervalHours hours.")
        }

        /**
         * Immediate one-time sync execution.
         */
        fun triggerOneTimeSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val oneTimeRequest = OneTimeWorkRequestBuilder<EventSyncWorker>()
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(context).enqueue(oneTimeRequest)
            Log.i(TAG, "One-time EventSyncWorker enqueued.")
        }

        fun cancelPeriodicSync(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }

    override suspend fun doWork(): Result {
        Log.i(TAG, "Starting background sync of tech conferences...")

        return try {
            val apiService = ConferenceApiService.getInstance(context)
            val store = LocalConferenceStore.getInstance(context)
            val settings = store.getAlertSettings()

            // 1. Fetch latest events from backend API
            val eventsResult = apiService.getEvents(days = 180)
            if (eventsResult.isFailure) {
                Log.w(TAG, "Sync: Failed to fetch events from API: ${eventsResult.exceptionOrNull()?.message}")
                return Result.retry()
            }

            val events = eventsResult.getOrNull() ?: emptyList()
            Log.i(TAG, "Sync: Successfully retrieved ${events.size} conferences.")

            // 2. Cache updated events locally
            store.cacheConferences(events)

            // 3. Scan for alert conditions matching user preferences
            for (conf in events) {
                // If user opted for Philippines-only alerts, skip global events
                if (settings.localPhOnly && !conf.isPhilippines) {
                    continue
                }

                when {
                    settings.remind0d && conf.daysUntil == 0 -> {
                        NotificationHelper.showConferenceAlert(context, conf, "reminder_0d")
                    }
                    settings.remind1d && conf.daysUntil == 1 -> {
                        NotificationHelper.showConferenceAlert(context, conf, "reminder_1d")
                    }
                    settings.remind3d && conf.daysUntil == 3 -> {
                        NotificationHelper.showConferenceAlert(context, conf, "reminder_3d")
                    }
                    settings.remind7d && conf.daysUntil == 7 -> {
                        NotificationHelper.showConferenceAlert(context, conf, "reminder_7d")
                    }
                    settings.cfpAlerts && conf.hasCfpOpen && conf.daysUntil in 1..14 -> {
                        NotificationHelper.showConferenceAlert(context, conf, "cfp_closing")
                    }
                }
            }

            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "Error in EventSyncWorker: ${e.message}", e)
            Result.retry()
        }
    }
}
