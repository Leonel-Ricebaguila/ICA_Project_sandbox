package com.upysentinel.nfc.network

import android.content.Context
import com.google.gson.Gson
import com.upysentinel.nfc.data.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.security.cert.X509Certificate
import javax.net.ssl.*

/**
 * Network manager for HTTPS communication with self-signed certificates
 */
class NetworkManager(private val context: Context) {
    
    private val gson = Gson()
    private val client: OkHttpClient
    
    companion object {
        private const val DEFAULT_BASE_URL = "https://192.168.1.84:5443"
        private const val PREFS_NAME = "app_prefs"
        private const val KEY_SERVER_URL = "server_url"
    }
    
    init {
        client = createTrustAllClient()
    }
    
    /**
     * Get current server URL (from SharedPreferences or default)
     */
    private fun getBaseUrl(): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_SERVER_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
    }
    
    /**
     * Update server URL and save to SharedPreferences
     */
    fun updateServerUrl(newUrl: String) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_SERVER_URL, newUrl).apply()
    }
    
    /**
     * Get current server URL for display
     */
    fun getCurrentServerUrl(): String {
        return getBaseUrl()
    }
    
    /**
     * Create OkHttpClient that trusts self-signed certificates
     */
    private fun createTrustAllClient(): OkHttpClient {
        val trustAllCerts = arrayOf<TrustManager>(object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) {}
            override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        })
        
        val sslContext = SSLContext.getInstance("SSL")
        sslContext.init(null, trustAllCerts, java.security.SecureRandom())
        val sslSocketFactory = sslContext.socketFactory
        
        return OkHttpClient.Builder()
            .sslSocketFactory(sslSocketFactory, trustAllCerts[0] as X509TrustManager)
            .hostnameVerifier { _, _ -> true }
            .build()
    }
    
    /**
     * Perform login request
     */
    suspend fun login(request: LoginRequest): Result<LoginResponse> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(request)
            val body = json.toRequestBody("application/json".toMediaType())
            
            val httpRequest = Request.Builder()
                .url("${getBaseUrl()}/api/auth/login")
                .post(body)
                .build()
            
            val response = client.newCall(httpRequest).execute()
            
            if (response.isSuccessful) {
                val responseBody = response.body?.string()
                val loginResponse = gson.fromJson(responseBody, LoginResponse::class.java)
                Result.success(loginResponse)
            } else {
                Result.failure(Exception("Login failed: ${response.code}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Activate device
     */
    suspend fun activateDevice(request: DeviceActivationRequest): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(request)
            val body = json.toRequestBody("application/json".toMediaType())
            
            val httpRequest = Request.Builder()
                .url("${getBaseUrl()}/api/device/activate")
                .post(body)
                .build()
            
            val response = client.newCall(httpRequest).execute()
            Result.success(response.isSuccessful)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Validate NFC card (IAM_Backend endpoint)
     */
    suspend fun validateCard(request: CardValidationRequest): Result<CardValidationResponse> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(request)
            val body = json.toRequestBody("application/json".toMediaType())
            
            val httpRequest = Request.Builder()
                .url("${getBaseUrl()}/api/nfc/scan")  // Updated for IAM_Backend
                .post(body)
                .build()
            
            val response = client.newCall(httpRequest).execute()
            
            if (response.isSuccessful) {
                val responseBody = response.body?.string()
                val validationResponse = gson.fromJson(responseBody, CardValidationResponse::class.java)
                Result.success(validationResponse)
            } else {
                Result.failure(Exception("Validation failed: ${response.code}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Send security alert
     */
    suspend fun sendSecurityAlert(alert: SecurityAlert): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val json = gson.toJson(alert)
            val body = json.toRequestBody("application/json".toMediaType())
            
            val httpRequest = Request.Builder()
                .url("${getBaseUrl()}/api/security/alert")
                .post(body)
                .build()
            
            val response = client.newCall(httpRequest).execute()
            Result.success(response.isSuccessful)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Register new card
     */
    suspend fun registerCard(card: NFCCard, authToken: String): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val requestBody = mapOf(
                "card" to card,
                "authToken" to authToken
            )
            val json = gson.toJson(requestBody)
            val body = json.toRequestBody("application/json".toMediaType())
            
            val httpRequest = Request.Builder()
                .url("${getBaseUrl()}/api/card/register")
                .post(body)
                .build()
            
            val response = client.newCall(httpRequest).execute()
            Result.success(response.isSuccessful)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Stop alarm (server command)
     */
    suspend fun stopAlarm(deviceId: String, authToken: String): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val requestBody = mapOf(
                "deviceId" to deviceId,
                "authToken" to authToken
            )
            val json = gson.toJson(requestBody)
            val body = json.toRequestBody("application/json".toMediaType())
            
            val httpRequest = Request.Builder()
                .url("${getBaseUrl()}/api/security/stop-alarm")
                .post(body)
                .build()
            
            val response = client.newCall(httpRequest).execute()
            Result.success(response.isSuccessful)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    /**
     * Get authentication token from SharedPreferences
     */
    private fun getAuthToken(): String {
        val prefs = context.getSharedPreferences("app_prefs", Context.MODE_PRIVATE)
        return prefs.getString("auth_token", "") ?: ""
    }
    
    /**
     * Get Android device ID
     */
    private fun getAndroidDeviceId(): String {
        return android.provider.Settings.Secure.getString(context.contentResolver, android.provider.Settings.Secure.ANDROID_ID)
    }
    
    /**
     * Check if alarm should be stopped from server
     * Queries /api/nfc/alarm/status/<device_id> to see if dashboard sent stop command
     */
    suspend fun checkAlarmStatus(): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            val deviceId = getAndroidDeviceId()
            val request = Request.Builder()
                .url("${getBaseUrl()}/api/nfc/alarm/status/$deviceId")
                .get()
                .build()
            
            val response = client.newCall(request).execute()
            
            if (response.isSuccessful) {
                val responseBody = response.body?.string()
                val jsonResponse = gson.fromJson(responseBody, Map::class.java)
                val shouldStop = jsonResponse["should_stop"] as? Boolean ?: false
                Result.success(shouldStop)
            } else {
                Result.failure(Exception("Server error: ${response.code}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

