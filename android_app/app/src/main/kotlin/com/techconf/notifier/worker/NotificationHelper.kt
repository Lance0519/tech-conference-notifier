package com.techconf.notifier.worker

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import com.techconf.notifier.MainActivity
import com.techconf.notifier.data.model.Conference

object NotificationHelper {

    const val CHANNEL_ID = "tech_conf_alerts_channel"
    private const val CHANNEL_NAME = "Tech Conference Alerts"
    private const val CHANNEL_DESCRIPTION = "Heads-up push notifications for upcoming IT & Tech conferences and CFP deadlines"

    const val EXTRA_EVENT_ID = "extra_event_id"
    const val EXTRA_TARGET_SCREEN = "extra_target_screen"

    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val importance = NotificationManager.IMPORTANCE_HIGH
            val channel = NotificationChannel(CHANNEL_ID, CHANNEL_NAME, importance).apply {
                description = CHANNEL_DESCRIPTION
                enableLights(true)
                enableVibration(true)
                setShowBadge(true)
            }
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    /**
     * Display a heads-up push notification for a specific conference event with action buttons.
     */
    fun showConferenceAlert(
        context: Context,
        conference: Conference,
        reminderType: String = "reminder"
    ) {
        createNotificationChannel(context)

        val notificationId = conference.id.hashCode()

        // 1. Content Intent: Opens App to this event
        val contentIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(EXTRA_EVENT_ID, conference.id)
            putExtra(EXTRA_TARGET_SCREEN, "explore")
        }
        val contentPendingIntent = PendingIntent.getActivity(
            context,
            notificationId,
            contentIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // 2. Action Intent: Direct "Open Website" in Browser
        val webIntent = Intent(Intent.ACTION_VIEW).apply {
            data = Uri.parse(if (conference.url.isNotBlank()) conference.url else "https://google.com")
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        val webPendingIntent = PendingIntent.getActivity(
            context,
            notificationId + 1,
            webIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val title = when (reminderType) {
            "reminder_0d" -> "🚨 Starts TODAY: ${conference.name}"
            "reminder_1d" -> "⏰ Tomorrow: ${conference.name}"
            "reminder_3d" -> "📅 In 3 Days: ${conference.name}"
            "reminder_7d" -> "🗓️ Next Week: ${conference.name}"
            "cfp_closing" -> "🎯 CFP Closing Soon: ${conference.name}"
            else -> "📢 Upcoming Conf: ${conference.name}"
        }

        val locationText = if (conference.isPhilippines) "🇵🇭 ${conference.locationStr}" else conference.locationStr
        val bodyText = "${conference.formattedDate} • $locationText\nCategory: ${conference.category}"
        val expandedText = "$bodyText\n\n${conference.description}"

        val defaultSoundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(bodyText)
            .setStyle(NotificationCompat.BigTextStyle().bigText(expandedText))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_EVENT)
            .setSound(defaultSoundUri)
            .setAutoCancel(true)
            .setContentIntent(contentPendingIntent)
            .addAction(
                android.R.drawable.ic_menu_view,
                "Open Website",
                webPendingIntent
            )
            .addAction(
                android.R.drawable.ic_menu_info_details,
                "View in App",
                contentPendingIntent
            )

        val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(notificationId, builder.build())
    }

    /**
     * Send an instant test push notification for verification.
     */
    fun showTestNotification(context: Context) {
        val sampleConf = Conference(
            id = "test_sample_01",
            name = "Philippine National IT Conference 2026",
            category = "Artificial Intelligence and Machine Learning",
            startDate = "2026-11-20",
            endDate = "2026-11-22",
            url = "https://example.com/ph-it-conf",
            locationStr = "SMX Convention Center, Pasay, Metro Manila",
            formattedDate = "Nov 20-22, 2026",
            daysUntil = 3,
            isPhilippines = true,
            hasCfpOpen = true,
            description = "The premier nationwide assembly of software engineers, AI researchers, and IT leaders in the Philippines."
        )
        showConferenceAlert(context, sampleConf, "reminder_3d")
    }
}
