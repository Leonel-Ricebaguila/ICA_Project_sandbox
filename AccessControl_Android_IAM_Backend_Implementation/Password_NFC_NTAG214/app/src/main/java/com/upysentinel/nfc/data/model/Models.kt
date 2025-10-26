package com.upysentinel.nfc.data.model

import java.security.MessageDigest
import java.security.SecureRandom
import java.util.*

/**
 * Data class representing an NFC card with security information
 */
data class NFCCard(
    val uid: String,
    val hash: String,
    val salt: String,
    val timestamp: Long = System.currentTimeMillis()
)

/**
 * Data class for login request
 */
data class LoginRequest(
    val email: String,  // IAM_Backend expects "email" not "username"
    val password: String,
    val deviceId: String
)

/**
 * Data class for login response from IAM_Backend
 */
data class LoginResponse(
    val uid: String,
    val rol: String,
    val session_id: String,
    val expires_at: Long
)

/**
 * Data class for device activation request
 */
data class DeviceActivationRequest(
    val deviceId: String,
    val authToken: String,
    val deviceInfo: DeviceInfo
)

/**
 * Data class for device information
 */
data class DeviceInfo(
    val model: String,
    val manufacturer: String,
    val androidVersion: String,
    val appVersion: String
)

/**
 * Data class for card validation request (IAM_Backend format)
 */
data class CardValidationRequest(
    val uid: String,
    val password_valid: Boolean,  // IAM_Backend uses snake_case
    val device_id: String,         // IAM_Backend uses snake_case
    val session_id: String          // IAM_Backend uses session_id instead of timestamp
)

/**
 * Data class for card validation response (IAM_Backend format)
 */
data class CardValidationResponse(
    val result: String,          // "granted" or "denied"
    val message: String,
    val reason: String? = null,   // Reason for denial (if denied)
    val user: User? = null,       // User info (if granted)
    val access_level: String? = null  // Access level (if granted)
)

/**
 * User data from IAM_Backend
 */
data class User(
    val uid: String,
    val nombre: String,
    val apellido: String,
    val rol: String
)

/**
 * Data class for security alert
 */
data class SecurityAlert(
    val deviceId: String,
    val uid: String?,
    val alertType: AlertType,
    val timestamp: Long,
    val failureCount: Int
)

enum class AlertType {
    MULTIPLE_FAILURES,
    CLONED_CARD,
    MALFORMED_CARD,
    UNAUTHORIZED_ACCESS
}

/**
 * Security utility class for hash generation and validation
 */
object SecurityUtils {
    private const val SALT_LENGTH = 16
    private val secureRandom = SecureRandom()
    
    /**
     * Generate a random salt
     */
    fun generateSalt(): String {
        val salt = ByteArray(SALT_LENGTH)
        secureRandom.nextBytes(salt)
        return Base64.getEncoder().encodeToString(salt)
    }
    
    /**
     * Generate hash from password, salt, and UID
     */
    fun generateHash(password: String, salt: String, uid: String): String {
        val input = "$password:$salt:$uid"
        val digest = MessageDigest.getInstance("SHA-256")
        val hashBytes = digest.digest(input.toByteArray())
        return Base64.getEncoder().encodeToString(hashBytes)
    }
    
    /**
     * Validate hash against password, salt, and UID
     */
    fun validateHash(password: String, salt: String, uid: String, expectedHash: String): Boolean {
        val calculatedHash = generateHash(password, salt, uid)
        return calculatedHash == expectedHash
    }
    
    /**
     * Convert byte array to hex string
     */
    fun bytesToHex(bytes: ByteArray): String {
        return bytes.joinToString("") { "%02X".format(it) }
    }
    
    /**
     * Convert hex string to byte array
     */
    fun hexToBytes(hex: String): ByteArray {
        val result = ByteArray(hex.length / 2)
        for (i in result.indices) {
            val index = i * 2
            result[i] = hex.substring(index, index + 2).toInt(16).toByte()
        }
        return result
    }
}

