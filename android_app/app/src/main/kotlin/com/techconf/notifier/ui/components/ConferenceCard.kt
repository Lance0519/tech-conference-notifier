package com.techconf.notifier.ui.components

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.techconf.notifier.data.model.Conference
import com.techconf.notifier.ui.theme.PhBadgeBg
import com.techconf.notifier.ui.theme.PhFlagBlue
import com.techconf.notifier.ui.theme.StatusCfpOpen
import com.techconf.notifier.ui.theme.StatusCfpOpenBg
import com.techconf.notifier.ui.theme.StatusNormal
import com.techconf.notifier.ui.theme.StatusNormalBg
import com.techconf.notifier.ui.theme.StatusStudentFriendly
import com.techconf.notifier.ui.theme.StatusStudentFriendlyBg
import com.techconf.notifier.ui.theme.StatusUrgent
import com.techconf.notifier.ui.theme.StatusUrgentBg
import com.techconf.notifier.ui.theme.StatusWarning
import com.techconf.notifier.ui.theme.StatusWarningBg

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ConferenceCard(
    conference: Conference,
    onBookmarkToggle: (Conference) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var showDetailDialog by remember { mutableStateOf(false) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable { showDetailDialog = true },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            // Badges Row
            FlowRow(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                // Countdown Badge
                CountdownBadge(conference = conference)

                // Category Badge
                CategoryBadge(category = conference.category)

                // Philippines Regional Badge
                if (conference.isPhilippines) {
                    PhilippinesBadge()
                }

                // Format Badge
                FormatBadge(format = conference.format)

                // Student Friendly Badge
                if (conference.isStudentFriendly) {
                    StudentFriendlyBadge()
                }

                // CFP Open Badge
                if (conference.hasCfpOpen) {
                    CfpBadge()
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Conference Name
            Text(
                text = conference.name,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )

            Spacer(modifier = Modifier.height(6.dp))

            // Date & Location
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "📅",
                    fontSize = 13.sp
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = if (conference.formattedDate.isNotBlank()) conference.formattedDate else conference.startDate,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Spacer(modifier = Modifier.height(4.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "📍",
                    fontSize = 13.sp
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = if (conference.locationStr.isNotBlank()) conference.locationStr else "${conference.city}, ${conference.country}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Student Eligibility Row
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "🎓",
                    fontSize = 13.sp
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    text = "Eligibility: Student-Friendly • Students & Pros",
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.SemiBold,
                    color = StatusStudentFriendly
                )
            }

            // Organizer / Audiences
            if (conference.organizer != "Not announced" && conference.organizer.isNotBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Hosted by: ${conference.organizer}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )
            }

            Spacer(modifier = Modifier.height(12.dp))
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
            Spacer(modifier = Modifier.height(8.dp))

            // Action Buttons Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Open Website Button
                FilledTonalButton(
                    onClick = {
                        openUrlInBrowser(context, conference.url)
                    },
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Text(text = "🌐 Open Website")
                }

                Row(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Share Button
                    IconButton(
                        onClick = {
                            shareConference(context, conference)
                        }
                    ) {
                        Text(text = "📤", fontSize = 18.sp)
                    }

                    // Bookmark Button
                    IconButton(
                        onClick = {
                            onBookmarkToggle(conference)
                        }
                    ) {
                        Text(
                            text = if (conference.isBookmarked) "❤️" else "🤍",
                            fontSize = 20.sp
                        )
                    }
                }
            }
        }
    }

    // Detail Dialog
    if (showDetailDialog) {
        ConferenceDetailDialog(
            conference = conference,
            onDismiss = { showDetailDialog = false },
            onBookmarkToggle = {
                onBookmarkToggle(conference)
            }
        )
    }
}

@Composable
fun CountdownBadge(conference: Conference) {
    val (bgColor, textColor) = when {
        conference.daysUntil in 0..2 -> StatusUrgentBg to StatusUrgent
        conference.daysUntil in 3..7 -> StatusWarningBg to StatusWarning
        else -> StatusNormalBg to StatusNormal
    }

    Surface(
        color = bgColor,
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = "⏳ ${conference.displayCountdownBadge}",
            color = textColor,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Composable
fun CategoryBadge(category: String) {
    Surface(
        color = MaterialTheme.colorScheme.primaryContainer,
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = category,
            color = MaterialTheme.colorScheme.onPrimaryContainer,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.SemiBold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Composable
fun PhilippinesBadge() {
    Surface(
        color = PhBadgeBg,
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = "🇵🇭 Philippines",
            color = PhFlagBlue,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Composable
fun FormatBadge(format: String) {
    val (label, icon) = when (format.lowercase()) {
        "virtual" -> "Virtual" to "💻"
        "hybrid" -> "Hybrid" to "🔀"
        else -> "In-Person" to "🏢"
    }

    Surface(
        color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.7f),
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = "$icon $label",
            color = MaterialTheme.colorScheme.onSecondaryContainer,
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Composable
fun StudentFriendlyBadge() {
    Surface(
        color = StatusStudentFriendlyBg,
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = "🎓 Student Friendly",
            color = StatusStudentFriendly,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Composable
fun CfpBadge() {
    Surface(
        color = StatusCfpOpenBg,
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(
            text = "🎯 CFP Open",
            color = StatusCfpOpen,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Composable
fun ConferenceDetailDialog(
    conference: Conference,
    onDismiss: () -> Unit,
    onBookmarkToggle: () -> Unit
) {
    val context = LocalContext.current

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = conference.name,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .verticalScroll(rememberScrollState())
                    .padding(vertical = 4.dp)
            ) {
                // Date & Time
                Text(
                    text = "🗓️ Schedule",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = "${conference.formattedDate} (${conference.timezone})",
                    style = MaterialTheme.typography.bodyMedium
                )

                Spacer(modifier = Modifier.height(10.dp))

                // Location
                Text(
                    text = "📍 Location",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = conference.locationStr,
                    style = MaterialTheme.typography.bodyMedium
                )

                Spacer(modifier = Modifier.height(10.dp))

                // Category & Topic
                Text(
                    text = "🏷️ Category",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = conference.category,
                    style = MaterialTheme.typography.bodyMedium
                )

                Spacer(modifier = Modifier.height(10.dp))

                // Description
                Text(
                    text = "📝 About Event",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = conference.description,
                    style = MaterialTheme.typography.bodyMedium
                )

                Spacer(modifier = Modifier.height(10.dp))

                // Eligibility & Audience Section
                Text(
                    text = "🎓 Eligibility & Target Audience",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(modifier = Modifier.height(4.dp))
                Surface(
                    color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f),
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(modifier = Modifier.padding(10.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(text = "✅ ", fontSize = 13.sp)
                            Text(
                                text = "Student-Friendly (Not for Professionals Only)",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onPrimaryContainer
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Senior high & college students, undergraduate/graduate researchers, self-taught developers, and beginners are warmly eligible and welcome to attend alongside industry professionals! Look out for discounted student passes, volunteer slots, and academic project showcases.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        FlowRow(
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                            verticalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            val audienceList = if (conference.targetAudiences.contains("Students")) {
                                conference.targetAudiences
                            } else {
                                listOf("Students") + conference.targetAudiences
                            }
                            audienceList.forEach { audience ->
                                Surface(
                                    color = MaterialTheme.colorScheme.surface,
                                    shape = RoundedCornerShape(6.dp)
                                ) {
                                    Text(
                                        text = when (audience.lowercase()) {
                                            "students" -> "🎓 Students"
                                            "developers" -> "💻 Developers"
                                            "researchers" -> "🔬 Researchers"
                                            "it executives" -> "👔 IT Executives"
                                            else -> "👥 $audience"
                                        },
                                        style = MaterialTheme.typography.labelSmall,
                                        fontWeight = FontWeight.SemiBold,
                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                    )
                                }
                            }
                        }
                    }
                }

                // CFP details
                if (conference.cfpDeadline != null || conference.cfpUrl != null) {
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = "🎯 Call For Papers (CFP)",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = StatusCfpOpen
                    )
                    conference.cfpDeadline?.let {
                        Text(text = "Deadline: $it", style = MaterialTheme.typography.bodyMedium)
                    }
                    conference.cfpUrl?.let { cfpLink ->
                        TextButton(
                            onClick = { openUrlInBrowser(context, cfpLink) },
                            modifier = Modifier.padding(0.dp)
                        ) {
                            Text(text = "Submit CFP / Paper Proposal ↗")
                        }
                    }
                }

                // Registration URL
                if (!conference.registrationUrl.isNullOrBlank()) {
                    Spacer(modifier = Modifier.height(6.dp))
                    TextButton(
                        onClick = { openUrlInBrowser(context, conference.registrationUrl) },
                        modifier = Modifier.padding(0.dp)
                    ) {
                        Text(text = "Register for Event ↗")
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "Organized by: ${conference.organizer}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )
                Text(
                    text = "Verification: ${conference.verificationStatus.replaceFirstChar { it.uppercase() }} • Source: ${conference.source}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.outline
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    openUrlInBrowser(context, conference.url)
                }
            ) {
                Text("Open Website")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}

fun openUrlInBrowser(context: Context, url: String) {
    if (url.isBlank()) {
        Toast.makeText(context, "No URL provided for this conference.", Toast.LENGTH_SHORT).show()
        return
    }
    try {
        val targetUrl = if (!url.startsWith("http://") && !url.startsWith("https://")) {
            "https://$url"
        } else {
            url
        }
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(targetUrl)).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        context.startActivity(intent)
    } catch (e: Exception) {
        Toast.makeText(context, "Could not open browser: ${e.message}", Toast.LENGTH_SHORT).show()
    }
}

fun shareConference(context: Context, conference: Conference) {
    try {
        val shareText = """
            🚀 Upcoming Tech Conference: ${conference.name}
            🗓️ Date: ${conference.formattedDate}
            📍 Location: ${conference.locationStr}
            🎓 Eligibility: Student-Friendly (Open to Students & Professionals)
            🏷️ Category: ${conference.category}
            🔗 Link: ${conference.url}
            
            Discovered via Tech Conference Notifier
        """.trimIndent()

        val sendIntent = Intent().apply {
            action = Intent.ACTION_SEND
            putExtra(Intent.EXTRA_TEXT, shareText)
            type = "text/plain"
        }
        val shareIntent = Intent.createChooser(sendIntent, "Share Conference")
        shareIntent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
        context.startActivity(shareIntent)
    } catch (e: Exception) {
        Toast.makeText(context, "Sharing failed: ${e.message}", Toast.LENGTH_SHORT).show()
    }
}
