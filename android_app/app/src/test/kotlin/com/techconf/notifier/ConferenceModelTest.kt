package com.techconf.notifier

import com.techconf.notifier.data.model.Conference
import com.techconf.notifier.data.model.MANDATORY_CATEGORIES
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ConferenceModelTest {

    @Test
    fun testMandatoryCategoriesCount() {
        assertEquals(16, MANDATORY_CATEGORIES.size)
        assertTrue(MANDATORY_CATEGORIES.contains("Computer Science"))
        assertTrue(MANDATORY_CATEGORIES.contains("Artificial Intelligence and Machine Learning"))
        assertTrue(MANDATORY_CATEGORIES.contains("Cybersecurity"))
        assertTrue(MANDATORY_CATEGORIES.contains("Cloud Computing and DevOps"))
    }

    @Test
    fun testConferenceSerializationAndDeserialization() {
        val conf = Conference(
            id = "conf_123",
            name = "PyCon Philippines 2026",
            category = "Software Engineering",
            source = "regional_ph",
            startDate = "2026-11-25",
            endDate = "2026-11-27",
            url = "https://pycon.ph",
            description = "Annual Python developer gathering in Manila",
            organizer = "Python Philippines",
            location = "SMX Aura, Taguig",
            city = "Taguig",
            country = "Philippines",
            geographicTier = "local_ph",
            format = "in_person",
            daysUntil = 3,
            isPhilippines = true,
            hasCfpOpen = true
        )

        val json = conf.toJson()
        assertEquals("conf_123", json.getString("id"))
        assertEquals("PyCon Philippines 2026", json.getString("name"))
        assertTrue(json.getBoolean("is_philippines"))

        val parsed = Conference.fromJson(json)
        assertEquals(conf.id, parsed.id)
        assertEquals(conf.name, parsed.name)
        assertEquals(conf.category, parsed.category)
        assertTrue(parsed.isPhilippines)
        assertTrue(parsed.hasCfpOpen)
        assertEquals("In 3 Days", parsed.displayCountdownBadge)
    }

    @Test
    fun testCountdownBadges() {
        val todayConf = Conference(
            id = "today_1",
            name = "DevCon Manila",
            startDate = "2026-11-11",
            daysUntil = 0
        )
        assertEquals("TODAY!", todayConf.displayCountdownBadge)

        val tomorrowConf = Conference(
            id = "tomorrow_1",
            name = "AWS Community Day",
            startDate = "2026-11-12",
            daysUntil = 1
        )
        assertEquals("Tomorrow", tomorrowConf.displayCountdownBadge)
    }

    @Test
    fun testStudentFriendlyEligibility() {
        val conf = Conference(
            id = "conf_student",
            name = "GDG DevFest Manila",
            startDate = "2026-12-12"
        )
        assertTrue(conf.isStudentFriendly)
        assertEquals("Open to Students & Professionals (Student-Friendly)", conf.eligibility)
        assertTrue(conf.targetAudiences.contains("Students"))

        val json = conf.toJson()
        assertEquals("Open to Students & Professionals (Student-Friendly)", json.getString("eligibility"))
        assertTrue(json.getBoolean("is_student_friendly"))

        val parsed = Conference.fromJson(json)
        assertTrue(parsed.isStudentFriendly)
        assertEquals("Open to Students & Professionals (Student-Friendly)", parsed.eligibility)
        assertTrue(parsed.targetAudiences.contains("Students"))
    }
}
