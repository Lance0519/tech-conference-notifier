package com.techconf.notifier.ui.screens

import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.techconf.notifier.data.api.ConferenceApiService
import com.techconf.notifier.data.model.CategorySummary
import com.techconf.notifier.data.model.MANDATORY_CATEGORIES
import kotlinx.coroutines.launch

@Composable
fun CategoriesScreen(
    onCategorySelected: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val apiService = remember { ConferenceApiService.getInstance(context) }

    var isLoading by remember { mutableStateOf(true) }
    var categories by remember { mutableStateOf<List<CategorySummary>>(emptyList()) }

    fun loadCategories() {
        scope.launch {
            isLoading = true
            val res = apiService.getCategories()
            if (res.isSuccess) {
                categories = res.getOrDefault(emptyList())
            } else {
                // Fallback to all 16 categories with 0 count
                categories = MANDATORY_CATEGORIES.map { CategorySummary(it, 0) }
            }
            isLoading = false
        }
    }

    LaunchedEffect(Unit) {
        loadCategories()
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp)
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        // Screen Header
        Text(
            text = "Explore by Discipline",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurface
        )
        Text(
            text = "16 Comprehensive IT & Computer Science Categories",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(12.dp))

        if (isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
        } else {
            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                contentPadding = PaddingValues(bottom = 24.dp),
                modifier = Modifier.fillMaxSize()
            ) {
                items(categories, key = { it.name }) { item ->
                    CategoryGridCard(
                        category = item,
                        onClick = { onCategorySelected(item.name) }
                    )
                }
            }
        }
    }
}

@Composable
fun CategoryGridCard(
    category: CategorySummary,
    onClick: () -> Unit
) {
    val icon = getCategoryIcon(category.name)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(130.dp)
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(14.dp),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Icon & Count Badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = icon,
                    fontSize = 28.sp
                )

                Surface(
                    color = MaterialTheme.colorScheme.primaryContainer,
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(
                        text = "${category.count} Events",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                    )
                }
            }

            // Category Name
            Text(
                text = category.name,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

fun getCategoryIcon(name: String): String {
    return when (name) {
        "Computer Science" -> "💻"
        "Information Technology" -> "🖥️"
        "Software Engineering" -> "⚙️"
        "Artificial Intelligence and Machine Learning" -> "🤖"
        "Data Science and Analytics" -> "📊"
        "Cybersecurity" -> "🔒"
        "Networking and Telecommunications" -> "🌐"
        "Cloud Computing and DevOps" -> "☁️"
        "Web and Mobile Development" -> "📱"
        "Game Development" -> "🎮"
        "Robotics and Internet of Things" -> "🦾"
        "Information Systems" -> "🗄️"
        "Database Management" -> "💾"
        "Computer Engineering" -> "🔌"
        "Emerging Technologies" -> "🚀"
        "Technology Entrepreneurship and Innovation" -> "💡"
        else -> "🏷️"
    }
}
