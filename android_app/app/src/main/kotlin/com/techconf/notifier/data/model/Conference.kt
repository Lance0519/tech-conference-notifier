package com.techconf.notifier.data.model

import org.json.JSONArray
import org.json.JSONObject
import java.io.Serializable

val MANDATORY_CATEGORIES = listOf(
    "Computer Science",
    "Information Technology",
    "Software Engineering",
    "Artificial Intelligence and Machine Learning",
    "Data Science and Analytics",
    "Cybersecurity",
    "Networking and Telecommunications",
    "Cloud Computing and DevOps",
    "Web and Mobile Development",
    "Game Development",
    "Robotics and Internet of Things",
    "Information Systems",
    "Database Management",
    "Computer Engineering",
    "Emerging Technologies",
    "Technology Entrepreneurship and Innovation"
)

data class Conference(
    val id: String,
    val name: String,
    val category: String = "Information Technology",
    val source: String = "unknown",
    val startDate: String, // YYYY-MM-DD
    val endDate: String? = null,
    val url: String = "",
    val normalizedName: String = "",
    val seriesSlug: String? = null,
    val subcategory: String? = null,
    val secondaryCategories: List<String> = emptyList(),
    val description: String = "Not available",
    val organizer: String = "Not announced",
    val startTime: String? = "Not announced",
    val timezone: String = "Asia/Manila",
    val location: String = "Not announced",
    val city: String = "Not announced",
    val country: String = "Not announced",
    val isoCountry: String? = null,
    val geographicTier: String = "international", // local_ph, sea_asean, international
    val format: String = "in_person", // in_person, virtual, hybrid
    val eventType: String = "conference", // conference, convention, summit, workshop, hackathon, meetup
    val registrationUrl: String? = null,
    val registrationDeadline: String? = null,
    val cfpDeadline: String? = null,
    val cfpUrl: String? = null,
    val feeType: String = "unknown", // free, paid, unknown
    val feeAmount: String = "Not announced",
    val status: String = "scheduled", // scheduled, ongoing, postponed, rescheduled, cancelled, completed
    val verificationStatus: String = "unverified", // verified, provisional, unverified, dead_link
    val confidenceScore: Double = 0.5,
    val targetAudiences: List<String> = listOf("Developers", "Students"),
    val eligibility: String = "Open to Students & Professionals (Student-Friendly)",
    val isStudentFriendly: Boolean = true,
    val locationStr: String = "",
    val formattedDate: String = "",
    val daysUntil: Int = 0,
    val statusLabel: String = "",
    val isOnline: Boolean = false,
    val isPhilippines: Boolean = false,
    val isFree: Boolean = false,
    val hasCfpOpen: Boolean = false,
    var isBookmarked: Boolean = false
) : Serializable {

    val isUrgent: Boolean
        get() = daysUntil in 0..3

    val isThisWeek: Boolean
        get() = daysUntil in 0..7

    val displayCountdownBadge: String
        get() = when {
            status == "cancelled" -> "CANCELLED"
            status == "postponed" -> "POSTPONED"
            daysUntil < 0 -> "Completed"
            daysUntil == 0 -> "TODAY!"
            daysUntil == 1 -> "Tomorrow"
            daysUntil <= 7 -> "In $daysUntil Days"
            daysUntil <= 30 -> "In $daysUntil Days"
            else -> "In ${daysUntil / 30} Mo"
        }

    val displayFormatLabel: String
        get() = when (format.lowercase()) {
            "virtual" -> "Virtual / Online"
            "hybrid" -> "Hybrid"
            else -> "In-Person"
        }

    fun toJson(): JSONObject {
        val obj = JSONObject()
        obj.put("id", id)
        obj.put("name", name)
        obj.put("category", category)
        obj.put("source", source)
        obj.put("start_date", startDate)
        obj.put("end_date", endDate ?: JSONObject.NULL)
        obj.put("url", url)
        obj.put("normalized_name", normalizedName)
        obj.put("series_slug", seriesSlug ?: JSONObject.NULL)
        obj.put("subcategory", subcategory ?: JSONObject.NULL)
        obj.put("secondary_categories", JSONArray(secondaryCategories))
        obj.put("description", description)
        obj.put("organizer", organizer)
        obj.put("start_time", startTime ?: JSONObject.NULL)
        obj.put("timezone", timezone)
        obj.put("location", location)
        obj.put("city", city)
        obj.put("country", country)
        obj.put("iso_country", isoCountry ?: JSONObject.NULL)
        obj.put("geographic_tier", geographicTier)
        obj.put("format", format)
        obj.put("event_type", eventType)
        obj.put("registration_url", registrationUrl ?: JSONObject.NULL)
        obj.put("registration_deadline", registrationDeadline ?: JSONObject.NULL)
        obj.put("cfp_deadline", cfpDeadline ?: JSONObject.NULL)
        obj.put("cfp_url", cfpUrl ?: JSONObject.NULL)
        obj.put("fee_type", feeType)
        obj.put("fee_amount", feeAmount)
        obj.put("status", status)
        obj.put("verification_status", verificationStatus)
        obj.put("confidence_score", confidenceScore)
        obj.put("target_audiences", JSONArray(targetAudiences))
        obj.put("eligibility", eligibility)
        obj.put("is_student_friendly", isStudentFriendly)
        obj.put("location_str", locationStr)
        obj.put("formatted_date", formattedDate)
        obj.put("days_until", daysUntil)
        obj.put("status_label", statusLabel)
        obj.put("is_online", isOnline)
        obj.put("is_philippines", isPhilippines)
        obj.put("is_free", isFree)
        obj.put("has_cfp_open", hasCfpOpen)
        obj.put("is_bookmarked", isBookmarked)
        return obj
    }

    companion object {
        fun fromJson(json: JSONObject): Conference {
            val secCats = mutableListOf<String>()
            val secCatsArr = json.optJSONArray("secondary_categories")
            if (secCatsArr != null) {
                for (i in 0 until secCatsArr.length()) {
                    secCats.add(secCatsArr.optString(i))
                }
            }

            val audiences = mutableListOf<String>()
            val audArr = json.optJSONArray("target_audiences")
            if (audArr != null) {
                for (i in 0 until audArr.length()) {
                    audiences.add(audArr.optString(i))
                }
            }
            if (audiences.isEmpty()) {
                audiences.add("Developers")
                audiences.add("Students")
            }

            val isStudentVal = json.optBoolean("is_student_friendly", true)
            val eligVal = json.optString("eligibility", "Open to Students & Professionals (Student-Friendly)")
            if (isStudentVal && !audiences.contains("Students")) {
                audiences.add("Students")
            }

            val formatVal = json.optString("format", "in_person")
            val isOnlineVal = json.optBoolean("is_online", formatVal in listOf("virtual", "hybrid"))
            val geoTier = json.optString("geographic_tier", "international")
            val isPhVal = json.optBoolean("is_philippines", geoTier == "local_ph")

            return Conference(
                id = json.optString("id", ""),
                name = json.optString("name", "Unnamed Conference"),
                category = json.optString("category", "Information Technology"),
                source = json.optString("source", "unknown"),
                startDate = json.optString("start_date", ""),
                endDate = if (json.isNull("end_date")) null else json.optString("end_date"),
                url = json.optString("url", ""),
                normalizedName = json.optString("normalized_name", ""),
                seriesSlug = if (json.isNull("series_slug")) null else json.optString("series_slug"),
                subcategory = if (json.isNull("subcategory")) null else json.optString("subcategory"),
                secondaryCategories = secCats,
                description = json.optString("description", "Not available"),
                organizer = json.optString("organizer", "Not announced"),
                startTime = if (json.isNull("start_time")) "Not announced" else json.optString("start_time"),
                timezone = json.optString("timezone", "Asia/Manila"),
                location = json.optString("location", "Not announced"),
                city = json.optString("city", "Not announced"),
                country = json.optString("country", "Not announced"),
                isoCountry = if (json.isNull("iso_country")) null else json.optString("iso_country"),
                geographicTier = geoTier,
                format = formatVal,
                eventType = json.optString("event_type", "conference"),
                registrationUrl = if (json.isNull("registration_url")) null else json.optString("registration_url"),
                registrationDeadline = if (json.isNull("registration_deadline")) null else json.optString("registration_deadline"),
                cfpDeadline = if (json.isNull("cfp_deadline")) null else json.optString("cfp_deadline"),
                cfpUrl = if (json.isNull("cfp_url")) null else json.optString("cfp_url"),
                feeType = json.optString("fee_type", "unknown"),
                feeAmount = json.optString("fee_amount", "Not announced"),
                status = json.optString("status", "scheduled"),
                verificationStatus = json.optString("verification_status", "unverified"),
                confidenceScore = json.optDouble("confidence_score", 0.5),
                targetAudiences = audiences,
                eligibility = eligVal,
                isStudentFriendly = isStudentVal,
                locationStr = json.optString("location_str", ""),
                formattedDate = json.optString("formatted_date", ""),
                daysUntil = json.optInt("days_until", 0),
                statusLabel = json.optString("status_label", ""),
                isOnline = isOnlineVal,
                isPhilippines = isPhVal,
                isFree = json.optBoolean("is_free", false),
                hasCfpOpen = json.optBoolean("has_cfp_open", false),
                isBookmarked = json.optBoolean("is_bookmarked", false)
            )
        }
    }
}

data class CategorySummary(
    val name: String,
    val count: Int
)

data class NotificationHistoryRecord(
    val id: Int,
    val eventId: String,
    val triggerType: String,
    val channel: String,
    val sentAt: String,
    val status: String
)

data class AlertSettings(
    val remind7d: Boolean = true,
    val remind3d: Boolean = true,
    val remind1d: Boolean = true,
    val remind0d: Boolean = true,
    val cfpAlerts: Boolean = true,
    val localPhOnly: Boolean = false,
    val syncIntervalHours: Int = 12
)
