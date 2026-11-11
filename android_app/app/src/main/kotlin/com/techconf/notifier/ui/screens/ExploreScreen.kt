package com.techconf.notifier.ui.screens

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.techconf.notifier.data.api.ConferenceApiService
import com.techconf.notifier.data.model.Conference
import com.techconf.notifier.data.model.MANDATORY_CATEGORIES
import com.techconf.notifier.ui.components.ConferenceCard
import com.techconf.notifier.ui.theme.StatusStudentFriendly
import com.techconf.notifier.ui.theme.StatusStudentFriendlyBg
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExploreScreen(
    initialCategory: String? = null,
    onCategoryReset: () -> Unit = {}
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val apiService = remember { ConferenceApiService.getInstance(context) }

    var searchQuery by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf<String?>(initialCategory) }
    var selectedRegion by remember { mutableStateOf("All") } // "All", "Philippines", "ASEAN", "Global"
    var selectedFormat by remember { mutableStateOf("All") } // "All", "in_person", "virtual", "hybrid"
    var cfpOnly by remember { mutableStateOf(false) }
    var studentFriendlyOnly by remember { mutableStateOf(false) }

    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var conferences by remember { mutableStateOf<List<Conference>>(emptyList()) }

    // Synchronize initialCategory if it changes from outside
    LaunchedEffect(initialCategory) {
        if (initialCategory != null && initialCategory != selectedCategory) {
            selectedCategory = initialCategory
        }
    }

    // Function to reload conferences
    fun loadConferences() {
        scope.launch {
            isLoading = true
            errorMessage = null

            val formatParam = if (selectedFormat != "All") selectedFormat else null
            val categoryParam = selectedCategory
            val countryParam = if (selectedRegion == "Philippines") "Philippines" else null

            val result = apiService.getEvents(
                category = categoryParam,
                format = formatParam,
                country = countryParam,
                search = if (searchQuery.isNotBlank()) searchQuery else null,
                days = 180
            )

            if (result.isSuccess) {
                var list = result.getOrNull() ?: emptyList()

                // Client side filters for finer granular criteria
                if (selectedRegion == "Philippines") {
                    list = list.filter { it.isPhilippines }
                } else if (selectedRegion == "ASEAN") {
                    list = list.filter { it.geographicTier == "sea_asean" }
                } else if (selectedRegion == "Global") {
                    list = list.filter { it.geographicTier == "international" }
                }

                if (cfpOnly) {
                    list = list.filter { it.hasCfpOpen }
                }

                if (studentFriendlyOnly) {
                    list = list.filter { it.isStudentFriendly || it.targetAudiences.contains("Students") }
                }

                conferences = list
            } else {
                errorMessage = result.exceptionOrNull()?.message ?: "Unable to load events"
            }
            isLoading = false
        }
    }

    // Trigger load when filter criteria change
    LaunchedEffect(selectedCategory, selectedRegion, selectedFormat, cfpOnly, studentFriendlyOnly) {
        loadConferences()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp)
    ) {
        // Student-Friendly Welcome Banner
        Surface(
            color = StatusStudentFriendlyBg.copy(alpha = 0.6f),
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 10.dp, bottom = 4.dp)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "🎓", fontSize = 20.sp)
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "Student-Friendly Tech Conferences",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = StatusStudentFriendly
                    )
                    Text(
                        text = "Conferences welcome students, learners & researchers — not for professionals only! Look for student passes & academic tracks.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Search Bar
        OutlinedTextField(
            value = searchQuery,
            onValueChange = {
                searchQuery = it
                loadConferences()
            },
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text("Search conferences, organizers, topics...") },
            leadingIcon = {
                Text(text = "🔍", fontSize = 16.sp, modifier = Modifier.padding(start = 8.dp))
            },
            trailingIcon = {
                if (searchQuery.isNotEmpty()) {
                    IconButton(onClick = {
                        searchQuery = ""
                        loadConferences()
                    }) {
                        Text(text = "✕", fontSize = 16.sp)
                    }
                }
            },
            singleLine = true,
            shape = RoundedCornerShape(14.dp)
        )

        Spacer(modifier = Modifier.height(10.dp))

        // Horizontal Filter Chips 1: Region & Format & CFP & Student-Friendly
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Student-Friendly Chip
            FilterChip(
                selected = studentFriendlyOnly,
                onClick = {
                    studentFriendlyOnly = !studentFriendlyOnly
                },
                label = { Text("🎓 Student Friendly") }
            )

            // Philippines Chip
            FilterChip(
                selected = selectedRegion == "Philippines",
                onClick = {
                    selectedRegion = if (selectedRegion == "Philippines") "All" else "Philippines"
                },
                label = { Text("🇵🇭 Philippines") }
            )

            // ASEAN Chip
            FilterChip(
                selected = selectedRegion == "ASEAN",
                onClick = {
                    selectedRegion = if (selectedRegion == "ASEAN") "All" else "ASEAN"
                },
                label = { Text("🌏 ASEAN") }
            )

            // Global Chip
            FilterChip(
                selected = selectedRegion == "Global",
                onClick = {
                    selectedRegion = if (selectedRegion == "Global") "All" else "Global"
                },
                label = { Text("🌐 Global") }
            )

            // CFP Open Chip
            FilterChip(
                selected = cfpOnly,
                onClick = { cfpOnly = !cfpOnly },
                label = { Text("🎯 CFP Open") }
            )

            // In-Person Chip
            FilterChip(
                selected = selectedFormat == "in_person",
                onClick = {
                    selectedFormat = if (selectedFormat == "in_person") "All" else "in_person"
                },
                label = { Text("🏢 In-Person") }
            )

            // Virtual Chip
            FilterChip(
                selected = selectedFormat == "virtual",
                onClick = {
                    selectedFormat = if (selectedFormat == "virtual") "All" else "virtual"
                },
                label = { Text("💻 Virtual") }
            )

            // Hybrid Chip
            FilterChip(
                selected = selectedFormat == "hybrid",
                onClick = {
                    selectedFormat = if (selectedFormat == "hybrid") "All" else "hybrid"
                },
                label = { Text("🔀 Hybrid") }
            )
        }

        Spacer(modifier = Modifier.height(6.dp))

        // Horizontal Filter Chips 2: 16 IT/CS Categories
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // All Categories Chip
            FilterChip(
                selected = selectedCategory == null,
                onClick = {
                    selectedCategory = null
                    onCategoryReset()
                },
                label = { Text("All Categories") }
            )

            MANDATORY_CATEGORIES.forEach { categoryName ->
                FilterChip(
                    selected = selectedCategory == categoryName,
                    onClick = {
                        selectedCategory = if (selectedCategory == categoryName) null else categoryName
                    },
                    label = { Text(categoryName) }
                )
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // Count Summary & Refresh Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "${conferences.size} Upcoming Conferences",
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            TextButton(onClick = { loadConferences() }) {
                Text(text = "🔄 Refresh")
            }
        }

        Spacer(modifier = Modifier.height(4.dp))

        // Main List Content
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            when {
                isLoading -> {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        CircularProgressIndicator()
                        Spacer(modifier = Modifier.height(12.dp))
                        Text("Finding upcoming tech conferences...")
                    }
                }
                errorMessage != null && conferences.isEmpty() -> {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center,
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Text(text = "⚠️", fontSize = 36.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Connection Notice",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = errorMessage ?: "Could not reach server.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.outline
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        TextButton(onClick = { loadConferences() }) {
                            Text("Retry")
                        }
                    }
                }
                conferences.isEmpty() -> {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center,
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Text(text = "🔍", fontSize = 42.sp)
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "No conferences found",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Try adjusting your search terms or filters.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.outline
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        TextButton(onClick = {
                            searchQuery = ""
                            selectedCategory = null
                            selectedRegion = "All"
                            selectedFormat = "All"
                            cfpOnly = false
                            studentFriendlyOnly = false
                            onCategoryReset()
                            loadConferences()
                        }) {
                            Text("Clear All Filters")
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(14.dp),
                        contentPadding = PaddingValues(bottom = 24.dp)
                    ) {
                        items(conferences, key = { it.id }) { conf ->
                            ConferenceCard(
                                conference = conf,
                                onBookmarkToggle = { target ->
                                    scope.launch {
                                        val res = apiService.toggleBookmark(target)
                                        if (res.isSuccess) {
                                            val isBookmarked = res.getOrDefault(false)
                                            conferences = conferences.map {
                                                if (it.id == target.id) it.copy(isBookmarked = isBookmarked) else it
                                            }
                                        }
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}
