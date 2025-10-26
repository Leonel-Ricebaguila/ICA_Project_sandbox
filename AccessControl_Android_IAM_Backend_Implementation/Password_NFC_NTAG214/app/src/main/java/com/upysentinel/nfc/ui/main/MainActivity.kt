package com.upysentinel.nfc.ui.main

import android.content.Intent
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.upysentinel.nfc.R
import com.upysentinel.nfc.audio.AudioFeedbackManager
import com.upysentinel.nfc.data.model.*
import com.upysentinel.nfc.databinding.ActivityMainBinding
import com.upysentinel.nfc.nfc.NFCManager
import com.upysentinel.nfc.network.NetworkManager
import com.upysentinel.nfc.ui.login.LoginActivity
import com.upysentinel.nfc.ui.programming.CardProgrammingActivity
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay
import kotlinx.coroutines.Job

class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private lateinit var nfcAdapter: NfcAdapter
    private lateinit var nfcManager: NFCManager
    private lateinit var networkManager: NetworkManager
    private lateinit var audioManager: AudioFeedbackManager
    
    private var alarmCheckJob: Job? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Initialize components
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        nfcManager = NFCManager()
        networkManager = NetworkManager(this)
        audioManager = AudioFeedbackManager(this)
        
        setupUI()
        checkNFCStatus()
    }
    
    private fun setupUI() {
        binding.programCardButton.setOnClickListener {
            startActivity(Intent(this, CardProgrammingActivity::class.java))
        }
        
        binding.stopAlarmButton.setOnClickListener {
            // Show message that alarm can only be stopped from server
            Toast.makeText(this, "Alarm can only be stopped from server CLI", Toast.LENGTH_LONG).show()
        }
        
        binding.logoutButton.setOnClickListener {
            logout()
        }
        
        // Update UI based on login status
        updateUI()
    }
    
    private fun checkNFCStatus() {
        if (!nfcAdapter.isEnabled) {
            binding.statusText.text = getString(R.string.nfc_disabled)
            binding.enableNfcButton.visibility = View.VISIBLE
            binding.enableNfcButton.setOnClickListener {
                startActivity(Intent(Settings.ACTION_NFC_SETTINGS))
            }
        } else {
            binding.statusText.text = getString(R.string.nfc_ready)
            binding.enableNfcButton.visibility = View.GONE
        }
    }
    
    private fun updateUI() {
        val prefs = getSharedPreferences("app_prefs", MODE_PRIVATE)
        val isLoggedIn = prefs.getBoolean("is_logged_in", false)
        val isActivated = prefs.getBoolean("device_activated", false)
        
        if (!isLoggedIn || !isActivated) {
            // Redirect to login if not properly authenticated
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }
        
        // Update UI elements
        binding.statusText.text = getString(R.string.welcome_message)
        
        // Check alarm status
        checkAlarmStatus()
    }
    
    private fun checkAlarmStatus() {
        if (audioManager.isAlarmActive()) {
            showAlarmButton()
            
            // Check if server wants to stop the alarm
            lifecycleScope.launch {
                android.util.Log.d("MainActivity", "Checking alarm status from server...")
                val result = networkManager.checkAlarmStatus()
                result.fold(
                    onSuccess = { shouldStop ->
                        android.util.Log.d("MainActivity", "Server response: shouldStop=$shouldStop")
                        if (shouldStop) {
                            android.util.Log.d("MainActivity", "Stopping alarm from server command")
                            audioManager.stopAlarm()
                            hideAlarmButton()
                            binding.statusText.text = "✅ Alarm stopped by administrator"
                            binding.statusText.setTextColor(getColor(R.color.success_color))
                            binding.statusText.visibility = View.VISIBLE
                            
                            // Hide status after 5 seconds
                            binding.statusText.postDelayed({
                                binding.statusText.visibility = View.GONE
                            }, 5000)
                        }
                    },
                    onFailure = { exception ->
                        // Server check failed, but alarm continues
                        android.util.Log.d("MainActivity", "Failed to check alarm status: ${exception.message}")
                    }
                )
            }
        } else {
            hideAlarmButton()
        }
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleNFCIntent(intent)
    }
    
    private fun handleNFCIntent(intent: Intent) {
        val tag = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableExtra(NfcAdapter.EXTRA_TAG, Tag::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra<Tag>(NfcAdapter.EXTRA_TAG)
        }
        if (tag != null) {
            processNFCTag(tag)
        }
    }
    
    private fun processNFCTag(tag: Tag) {
        lifecycleScope.launch {
            try {
                binding.statusText.text = getString(R.string.processing_card)
                binding.statusText.visibility = View.VISIBLE
                
                // Read UID
                val uid = nfcManager.readUID(tag)
                
                // Validate password using PWD_AUTH command
                val passwordValid = nfcManager.validatePassword(tag)
                
                // Validate card with server
                validateCardWithServer(uid, passwordValid)
                
            } catch (e: Exception) {
                handleCardError("Error processing card: ${e.message}")
            }
        }
    }
    
    private suspend fun validateCardWithServer(uid: String, passwordValid: Boolean) {
        val deviceId = getAndroidDeviceId()
        val sessionId = getSessionId()  // Get session_id from SharedPreferences
        
        val validationRequest = CardValidationRequest(uid, passwordValid, deviceId, sessionId)
        
        val result = networkManager.validateCard(validationRequest)
        
        result.fold(
            onSuccess = { response ->
                handleValidationResponse(response, uid)
            },
            onFailure = { exception ->
                handleCardError("Server validation failed: ${exception.message}")
            }
        )
    }
    
    private fun getSessionId(): String {
        val prefs = getSharedPreferences("app_prefs", MODE_PRIVATE)
        return prefs.getString("auth_token", "") ?: ""
    }
    
    private fun handleValidationResponse(response: CardValidationResponse, uid: String) {
        if (response.result == "granted") {
            // Valid access - show user info
            val userName = response.user?.let { "${it.nombre} ${it.apellido}" } ?: "User"
            binding.statusText.text = "✓ Access Granted: $userName"
            binding.statusText.setTextColor(getColor(R.color.success_color))
            
            // Use AudioFeedbackManager to handle success
            audioManager.handleAccessAttempt(true) {
                // Success callback - no security alert needed
            }
            
        } else {
            // Invalid access - show denial reason
            val reason = response.reason ?: "unknown"
            binding.statusText.text = "✗ Access Denied: $reason"
            binding.statusText.setTextColor(getColor(R.color.error_color))
            
            // Use AudioFeedbackManager to handle failure
            audioManager.handleAccessAttempt(false) {
                // Security alert callback - only send if password was invalid
                if (reason == "invalid_password") {
                    showAlarmButton()
                }
            }
        }
        
        binding.statusText.visibility = View.VISIBLE
        
        // Hide status after 3 seconds
        binding.statusText.postDelayed({
            binding.statusText.visibility = View.GONE
        }, 3000)
    }
    
    private fun showAlarmButton() {
        android.util.Log.d("MainActivity", "showAlarmButton() called")
        
        binding.stopAlarmButton.visibility = View.VISIBLE
        binding.statusText.text = "🚨 SECURITY ALERT: Alarm active - Contact administrator 🚨"
        binding.statusText.setTextColor(getColor(R.color.error_color))
        binding.statusText.visibility = View.VISIBLE
        
        // Make the status text persistent (don't hide it)
        binding.statusText.postDelayed({
            // Don't hide the status text when alarm is active
            if (audioManager.isAlarmActive()) {
                binding.statusText.visibility = View.VISIBLE
            }
        }, 3000)
        
        // Disable ALL buttons when alarm is active (including logout)
        binding.programCardButton.isEnabled = false
        binding.programCardButton.alpha = 0.5f
        binding.logoutButton.isEnabled = false
        binding.logoutButton.alpha = 0.5f
        
        // Start periodic alarm status check
        android.util.Log.d("MainActivity", "Starting periodic alarm status check")
        startAlarmStatusCheck()
        android.util.Log.d("MainActivity", "showAlarmButton() completed")
    }
    
    private fun hideAlarmButton() {
        binding.stopAlarmButton.visibility = View.GONE
        binding.statusText.text = getString(R.string.welcome_message)
        binding.statusText.setTextColor(getColor(R.color.upy_primary))
        
        // Re-enable all buttons
        binding.programCardButton.isEnabled = true
        binding.programCardButton.alpha = 1.0f
        binding.logoutButton.isEnabled = true
        binding.logoutButton.alpha = 1.0f
        
        // Stop periodic alarm status check
        stopAlarmStatusCheck()
    }
    
    private fun startAlarmStatusCheck() {
        alarmCheckJob?.cancel()
        alarmCheckJob = lifecycleScope.launch {
            while (audioManager.isAlarmActive()) {
                android.util.Log.d("MainActivity", "Periodic alarm status check...")
                checkServerForAlarmStop()
                delay(5000) // Check every 5 seconds
            }
        }
    }
    
    private fun stopAlarmStatusCheck() {
        alarmCheckJob?.cancel()
        alarmCheckJob = null
    }
    
    private suspend fun checkServerForAlarmStop() {
        val result = networkManager.checkAlarmStatus()
        result.fold(
            onSuccess = { shouldStop ->
                android.util.Log.d("MainActivity", "Periodic check - shouldStop: $shouldStop")
                if (shouldStop) {
                    android.util.Log.d("MainActivity", "Stopping alarm from periodic check")
                    audioManager.stopAlarm()
                    hideAlarmButton()
                    binding.statusText.text = "✅ Alarm stopped by administrator"
                    binding.statusText.setTextColor(getColor(R.color.success_color))
                    binding.statusText.visibility = View.VISIBLE
                    
                    // Hide status after 5 seconds
                    binding.statusText.postDelayed({
                        binding.statusText.visibility = View.GONE
                    }, 5000)
                }
            },
            onFailure = { exception ->
                android.util.Log.d("MainActivity", "Periodic check failed: ${exception.message}")
            }
        )
    }
    
    // Security alerts are handled automatically by IAM_Backend through /api/nfc/scan
    // No need for separate security alert endpoint
    private fun sendSecurityAlert(uid: String, response: CardValidationResponse) {
        android.util.Log.d("MainActivity", "Security event logged by IAM_Backend: $uid")
        // IAM_Backend automatically logs all scan attempts in the eventos table
    }
    
    private fun handleCardError(message: String) {
        android.util.Log.d("MainActivity", "handleCardError: $message")
        
        binding.statusText.text = message
        binding.statusText.setTextColor(getColor(R.color.error_color))
        binding.statusText.visibility = View.VISIBLE
        
        // Use AudioFeedbackManager to handle failure and trigger alarm if needed
        android.util.Log.d("MainActivity", "Calling audioManager.handleAccessAttempt(false)")
        audioManager.handleAccessAttempt(false) {
            android.util.Log.d("MainActivity", "Security alert callback triggered!")
            android.util.Log.d("MainActivity", "Failure count: ${audioManager.getFailureCount()}")
            android.util.Log.d("MainActivity", "Is alarm active: ${audioManager.isAlarmActive()}")
            
            // Security events are automatically logged by IAM_Backend through /api/nfc/scan
            android.util.Log.d("MainActivity", "Security event logged by IAM_Backend")
            
            // Show alarm button if alarm is triggered
            android.util.Log.d("MainActivity", "Calling showAlarmButton()")
            showAlarmButton()
            android.util.Log.d("MainActivity", "showAlarmButton() completed")
        }
        
        // Hide status after 3 seconds
        binding.statusText.postDelayed({
            binding.statusText.visibility = View.GONE
        }, 3000)
    }
    
    private fun getAndroidDeviceId(): String {
        return Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
    }
    
    private fun logout() {
        val prefs = getSharedPreferences("app_prefs", MODE_PRIVATE)
        prefs.edit()
            .clear()
            .apply()
        
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }
    
    override fun onResume() {
        super.onResume()
        
        // Check alarm status when resuming
        checkAlarmStatus()
        
        // Enable NFC foreground dispatch
        if (nfcAdapter.isEnabled) {
            val intent = Intent(this, javaClass).addFlags(Intent.FLAG_RECEIVER_REPLACE_PENDING)
            val pendingIntent = android.app.PendingIntent.getActivity(
                this, 0, intent, android.app.PendingIntent.FLAG_MUTABLE
            )
            
            val filters = arrayOf(
                android.content.IntentFilter(android.nfc.NfcAdapter.ACTION_TECH_DISCOVERED)
            )
            
            val techLists = arrayOf(
                arrayOf(android.nfc.tech.NfcA::class.java.name)
            )
            
            nfcAdapter.enableForegroundDispatch(this, pendingIntent, filters, techLists)
        }
    }
    
    override fun onPause() {
        super.onPause()
        
        // Disable NFC foreground dispatch
        nfcAdapter.disableForegroundDispatch(this)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        
        // Cancel alarm check job
        alarmCheckJob?.cancel()
    }
}
