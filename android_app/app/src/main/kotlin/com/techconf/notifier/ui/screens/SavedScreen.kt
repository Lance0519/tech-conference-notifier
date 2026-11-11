package com.techconf.notifier.ui.screens

import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.techconf.notifier.data.api.ConferenceApiService
import com.techconf.notifier.data.local.LocalConferenceStore
import com.techconf.notifier.data.model.Conference
import com.techconf.notifier.ui.components.ConferenceCard
import kotlinx.coroutines.launch

@Composable
fun SavedScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val apiService = remember { ConferenceApiService.getInstance(context) }
    val store = remember { LocalConferenceStore.getInstance(context) }

    var savedEvents by remember { mutableStateOf<List<Conference>>(emptyList()) }
    var searchQuery by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(true) }

    fun loadBookmarks() {
        scope.launch {
            isLoading = true
            // Local store gives instant offline availability
            val localList = store.getSavedBookmarks()
            savedEvents = localList

            // Also attempt server sync in background if online
            val res = apiService.getBookmarks()
            if (res.isSuccess) {
                savedEvents = res.getOrDefault(localList)
            }
            isLoading = false
        }
    }

    LaunchedEffect(Unit) {
        loadBookmarks()
    }

    val filteredList = remember(savedEvents, searchQuery) {
        if (searchQuery.isBlank()) {
            savedEvents
        } else {
            val q = searchQuery.lowercase()
            savedEvents.filter {
                it.name.lowercase().contains(q) ||
                        it.category.lowercase().contains(q) ||
                        it.locationStr.lowercase().contains(q)
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp)
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        // Screen Header
        Text(
            text = "Saved Conferences",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )

        // Offline Ready Banner
        Surface(
            color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.5f),
            shape = RoundedCornerShape(10.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp)
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "💾", fontSize = 16.sp)
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Offline Ready: All saved conferences are accessible without internet.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer
                )
            }
        }

        // Search Bar for Saved Events
        if (savedEvents.isNotEmpty()) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("Filter your saved events...") },
                leadingIcon = { Text(text = "🔍", fontSize = 16.sp) },
                singleLine = true,
                shape = RoundedCornerShape(14.dp)
            )
            Spacer(modifier = Modifier.height(12.dp))
        }

        // Content
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            when {
                isLoading && savedEvents.isEmpty() -> {
                    CircularProgressIndicator()
                }
                savedEvents.isEmpty() -> {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center,
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Text(text = "🔖", fontSize = 48.sp)
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "No saved conferences yet",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Tap the heart or bookmark icon on any conference card to save it for offline access and timely notifications.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.outline
                        )
                    }
                }
                filteredList.isEmpty() -> {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        Text(text = "No matching saved conferences.")
                        TextButton(onClick = { searchQuery = "" }) {
                            Text("Clear Search")
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(14.dp),
                        contentPadding = PaddingValues(bottom = 24.dp)
                    ) {
                        items(filteredList, key = { it.id }) { conf ->
                            ConferenceCard(
                                conference = conf,
                                onBookmarkToggle = { target ->
                                    scope.launch {
                                        apiService.toggleBookmark(target)
                                        // Update list instantly
                                        savedEvents = savedEvents.filter { it.id != target.id }
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
