package com.techconf.notifier.ui.screens

import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.techconf.notifier.data.api.ConferenceApiService
import com.techconf.notifier.data.local.LocalConferenceStore
import com.techconf.notifier.data.model.AlertSettings
import com.techconf.notifier.data.model.NotificationHistoryRecord
import com.techconf.notifier.worker.EventSyncWorker
import com.techconf.notifier.worker.NotificationHelper
import kotlinx.coroutines.launch

@Composable
fun AlertsScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val store = remember { LocalConferenceStore.getInstance(context) }
    val apiService = remember { ConferenceApiService.getInstance(context) }

    var alertSettings by remember { mutableStateOf(store.getAlertSettings()) }
    var notificationHistory by remember { mutableStateOf<List<NotificationHistoryRecord>>(emptyList()) }
    var isSyncing by remember { mutableStateOf(false) }
    var showServerConfigDialog by remember { mutableStateOf(false) }
    var currentServerUrl by remember { mutableStateOf(store.getBaseUrl()) }

    fun updateSettings(newSettings: AlertSettings) {
        alertSettings = newSettings
        store.saveAlertSettings(newSettings)
        // Re-schedule WorkManager sync with configured interval
        EventSyncWorker.schedulePeriodicSync(context, newSettings.syncIntervalHours.toLong())
    }

    fun loadHistory() {
        scope.launch {
            val res = apiService.getNotifications()
            if (res.isSuccess) {
                notificationHistory = res.getOrDefault(emptyList())
            }
        }
    }

    LaunchedEffect(Unit) {
        loadHistory()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        // Screen Header
        Text(
            text = "Alerts & Notifications",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Text(
            text = "Configure reminder intervals and automated background sync",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Reminder Intervals Card
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            ),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "🔔 Reminder Windows",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )

                Spacer(modifier = Modifier.height(8.dp))

                // 7 Days
                AlertToggleRow(
                    title = "7 Days Before Event",
                    subtitle = "One week advance reminder for travel and logistics",
                    checked = alertSettings.remind7d,
                    onCheckedChange = { updateSettings(alertSettings.copy(remind7d = it)) }
                )

                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                // 3 Days
                AlertToggleRow(
                    title = "3 Days Before Event",
                    subtitle = "Final scheduling and preparation reminder",
                    checked = alertSettings.remind3d,
                    onCheckedChange = { updateSettings(alertSettings.copy(remind3d = it)) }
                )

                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                // 1 Day
                AlertToggleRow(
                    title = "1 Day Before Event (Eve)",
                    subtitle = "Tomorrow countdown notification",
                    checked = alertSettings.remind1d,
                    onCheckedChange = { updateSettings(alertSettings.copy(remind1d = it)) }
                )

                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                // 0 Days / Event Day
                AlertToggleRow(
                    title = "Event Day (0 Days)",
                    subtitle = "Morning alert when conference starts today",
                    checked = alertSettings.remind0d,
                    onCheckedChange = { updateSettings(alertSettings.copy(remind0d = it)) }
                )

                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                // CFP Deadlines
                AlertToggleRow(
                    title = "Call For Papers (CFP) Deadlines",
                    subtitle = "Heads-up alert when paper submission is closing soon",
                    checked = alertSettings.cfpAlerts,
                    onCheckedChange = { updateSettings(alertSettings.copy(cfpAlerts = it)) }
                )

                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                // Philippines Only
                AlertToggleRow(
                    title = "🇵🇭 Philippines Events Only",
                    subtitle = "Only push reminders for events held locally in the Philippines",
                    checked = alertSettings.localPhOnly,
                    onCheckedChange = { updateSettings(alertSettings.copy(localPhOnly = it)) }
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Background Sync Interval Card
        Card(
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
            ),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "⚙️ Background WorkManager Sync",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = "Periodic sync runs in the background even when app is closed.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    FilledTonalButton(
                        onClick = { updateSettings(alertSettings.copy(syncIntervalHours = 12)) },
                        modifier = Modifier.weight(1f),
                        colors = if (alertSettings.syncIntervalHours == 12) {
                            ButtonDefaults.filledTonalButtonColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                        } else {
                            ButtonDefaults.filledTonalButtonColors()
                        }
                    ) {
                        Text(text = if (alertSettings.syncIntervalHours == 12) "✓ Every 12 Hours" else "Every 12 Hours")
                    }

                    FilledTonalButton(
                        onClick = { updateSettings(alertSettings.copy(syncIntervalHours = 24)) },
                        modifier = Modifier.weight(1f),
                        colors = if (alertSettings.syncIntervalHours == 24) {
                            ButtonDefaults.filledTonalButtonColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                        } else {
                            ButtonDefaults.filledTonalButtonColors()
                        }
                    ) {
                        Text(text = if (alertSettings.syncIntervalHours == 24) "✓ Every 24 Hours" else "Every 24 Hours")
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Live Actions: Test Push & Immediate Sync
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            // Test Notification Button
            OutlinedButton(
                onClick = {
                    NotificationHelper.showTestNotification(context)
                    Toast.makeText(context, "Heads-up notification triggered!", Toast.LENGTH_SHORT).show()
                },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(12.dp)
            ) {
                Text(text = "🧪 Test Push Alert")
            }

            // Sync Now Button
            Button(
                onClick = {
                    scope.launch {
                        isSyncing = true
                        EventSyncWorker.triggerOneTimeSync(context)
                        val res = apiService.triggerSync()
                        if (res.isSuccess) {
                            Toast.makeText(context, "Sync completed successfully!", Toast.LENGTH_SHORT).show()
                            loadHistory()
                        } else {
                            Toast.makeText(context, "Sync triggered locally.", Toast.LENGTH_SHORT).show()
                        }
                        isSyncing = false
                    }
                },
                modifier = Modifier.weight(1f),
                shape = RoundedCornerShape(12.dp),
                enabled = !isSyncing
            ) {
                if (isSyncing) {
                    CircularProgressIndicator(
                        modifier = Modifier.width(18.dp).height(18.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text(text = "🔄 Sync Now")
                }
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // Server Host Config Link
        TextButton(
            onClick = { showServerConfigDialog = true },
            modifier = Modifier.align(Alignment.CenterHorizontally)
        ) {
            Text(text = "🔧 Configure Backend Host (${currentServerUrl})")
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Notification History Section
        Text(
            text = "📜 Recent Alert History",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )

        Spacer(modifier = Modifier.height(8.dp))

        if (notificationHistory.isEmpty()) {
            Surface(
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "No alerts logged yet. Reminders will appear here once dispatched.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline,
                    modifier = Modifier.padding(16.dp)
                )
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                notificationHistory.forEach { item ->
                    NotificationHistoryItemRow(item)
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))
    }

    // Backend Config Dialog
    if (showServerConfigDialog) {
        var tempUrl by remember { mutableStateOf(currentServerUrl) }

        AlertDialog(
            onDismissRequest = { showServerConfigDialog = false },
            title = { Text("Connection & Sync Mode") },
            text = {
                Column {
                    Text(
                        text = "• Standalone Mode: Runs 100% independently using only Wi-Fi/cellular. No PC or local server needed!\n• Custom Mode: Connects to a self-hosted or cloud API.\n\nType 'standalone' for independent Wi-Fi mode.",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedTextField(
                        value = tempUrl,
                        onValueChange = { tempUrl = it },
                        label = { Text("Mode / Base URL") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    FilledTonalButton(
                        onClick = { tempUrl = "standalone" },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Reset to Standalone (Wi-Fi Only)", fontSize = 12.sp)
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val clean = tempUrl.trim().removeSuffix("/")
                        currentServerUrl = clean
                        store.setBaseUrl(clean)
                        apiService.baseUrl = clean
                        showServerConfigDialog = false
                        Toast.makeText(context, "API URL updated to $clean", Toast.LENGTH_SHORT).show()
                    }
                ) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(onClick = { showServerConfigDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun AlertToggleRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.outline
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange
        )
    }
}

@Composable
fun NotificationHistoryItemRow(item: NotificationHistoryRecord) {
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "${item.triggerType.replace('_', ' ').uppercase()} • ${item.channel}",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = "Event ID: ${item.eventId.take(12)}",
                    style = MaterialTheme.typography.bodySmall
                )
                if (item.sentAt.isNotBlank()) {
                    Text(
                        text = item.sentAt,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                }
            }

            Surface(
                color = MaterialTheme.colorScheme.primaryContainer,
                shape = RoundedCornerShape(8.dp)
            ) {
                Text(
                    text = item.status.uppercase(),
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                )
            }
        }
    }
}
