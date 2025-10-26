package com.upysentinel.nfc.ui.login

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.upysentinel.nfc.R
import com.upysentinel.nfc.data.model.*
import com.upysentinel.nfc.network.NetworkManager
import com.upysentinel.nfc.ui.main.MainActivity
import com.upysentinel.nfc.databinding.ActivityLoginBinding
import kotlinx.coroutines.launch

class LoginActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityLoginBinding
    private lateinit var networkManager: NetworkManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        networkManager = NetworkManager(this)
        
        setupUI()
    }
    
    private fun setupUI() {
        binding.loginButton.setOnClickListener {
            performLogin()
        }
        
        binding.settingsButton.setOnClickListener {
            showServerSettingsDialog()
        }
        
        // Check if already logged in
        if (isLoggedIn()) {
            navigateToMain()
        }
    }
    
    private fun showServerSettingsDialog() {
        val currentUrl = networkManager.getCurrentServerUrl()
        
        // Create input field
        val input = EditText(this).apply {
            setText(currentUrl)
            hint = "https://192.168.1.100:8443"
            setPadding(50, 30, 50, 30)
        }
        
        AlertDialog.Builder(this)
            .setTitle("Server Configuration")
            .setMessage("Enter server IP address and port:\n(e.g., https://192.168.1.84:8443)")
            .setView(input)
            .setPositiveButton("Save") { _, _ ->
                val newUrl = input.text.toString().trim()
                if (newUrl.isNotEmpty()) {
                    if (isValidUrl(newUrl)) {
                        networkManager.updateServerUrl(newUrl)
                        Toast.makeText(
                            this,
                            "Server URL updated to:\n$newUrl",
                            Toast.LENGTH_LONG
                        ).show()
                    } else {
                        Toast.makeText(
                            this,
                            "Invalid URL format. Use: https://IP:PORT",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }
            }
            .setNegativeButton("Cancel", null)
            .setNeutralButton("Reset to Default") { _, _ ->
                networkManager.updateServerUrl("https://192.168.1.84:5443")
                Toast.makeText(
                    this,
                    "Server URL reset to default",
                    Toast.LENGTH_SHORT
                ).show()
            }
            .show()
    }
    
    private fun isValidUrl(url: String): Boolean {
        return url.startsWith("http://") || url.startsWith("https://")
    }
    
    private fun performLogin() {
        val email = binding.usernameEditText.text.toString().trim()
        val password = binding.passwordEditText.text.toString().trim()
        
        if (email.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, "Please enter both email and password", Toast.LENGTH_SHORT).show()
            return
        }
        
        showLoading(true)
        
        val deviceId = getAndroidDeviceId()
        val loginRequest = LoginRequest(email, password, deviceId)
        
        lifecycleScope.launch {
            val result = networkManager.login(loginRequest)
            
            result.fold(
                onSuccess = { response ->
                    // IAM_Backend returns: uid, rol, session_id, expires_at
                    saveLoginData(response.session_id, response.uid, response.rol)
                    
                    // IAM_Backend doesn't have device activation endpoint
                    // Session ID from login is sufficient for authentication
                    saveDeviceActivation(true)
                    navigateToMain()
                },
                onFailure = { exception ->
                    showError("Network error: ${exception.message}")
                }
            )
            
            showLoading(false)
        }
    }
    
    // Device activation not needed for IAM_Backend
    // Session ID from login is sufficient
    
    private fun navigateToMain() {
        val intent = Intent(this, MainActivity::class.java)
        startActivity(intent)
        finish()
    }
    
    private fun showLoading(show: Boolean) {
        binding.loginButton.isEnabled = !show
        binding.usernameEditText.isEnabled = !show
        binding.passwordEditText.isEnabled = !show
        
        if (show) {
            binding.loginButton.text = getString(R.string.login_loading)
        } else {
            binding.loginButton.text = getString(R.string.login_button)
        }
    }
    
    private fun showError(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
    
    private fun getAndroidDeviceId(): String {
        return Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
    }
    
    private fun saveLoginData(sessionId: String, uid: String, rol: String) {
        val prefs = getSharedPreferences("app_prefs", MODE_PRIVATE)
        prefs.edit()
            .putString("auth_token", sessionId)
            .putString("user_uid", uid)
            .putString("user_rol", rol)
            .putBoolean("is_logged_in", true)
            .apply()
    }
    
    private fun saveDeviceActivation(activated: Boolean) {
        val prefs = getSharedPreferences("app_prefs", MODE_PRIVATE)
        prefs.edit()
            .putBoolean("device_activated", activated)
            .apply()
    }
    
    private fun isLoggedIn(): Boolean {
        val prefs = getSharedPreferences("app_prefs", MODE_PRIVATE)
        return prefs.getBoolean("is_logged_in", false) && 
               prefs.getBoolean("device_activated", false)
    }
}
