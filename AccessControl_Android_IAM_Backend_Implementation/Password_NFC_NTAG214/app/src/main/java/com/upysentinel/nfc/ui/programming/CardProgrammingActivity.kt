package com.upysentinel.nfc.ui.programming

import android.app.PendingIntent
import android.content.Intent
import android.content.IntentFilter
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
import com.upysentinel.nfc.nfc.NFCManager
import com.upysentinel.nfc.network.NetworkManager
import com.upysentinel.nfc.databinding.ActivityCardProgrammingBinding
import kotlinx.coroutines.launch

class CardProgrammingActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityCardProgrammingBinding
    private lateinit var nfcAdapter: NfcAdapter
    private lateinit var nfcManager: NFCManager
    private lateinit var networkManager: NetworkManager
    private lateinit var audioManager: AudioFeedbackManager
    private lateinit var pendingIntent: PendingIntent
    
    private var currentPassword = ""
    private var isProgramming = false
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityCardProgrammingBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        initializeComponents()
        setupUI()
        setupNFC()
    }
    
    private fun initializeComponents() {
        nfcManager = NFCManager()
        networkManager = NetworkManager(this)
        audioManager = AudioFeedbackManager(this)
        
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
    }
    
    private fun setupUI() {
        binding.programButton.setOnClickListener {
            val password = binding.passwordEditText.text.toString().trim()
            
            if (password.isEmpty()) {
                Toast.makeText(this, "Please enter a password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            
            if (password.length < 4) {
                Toast.makeText(this, "Password must be at least 4 characters", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            
            currentPassword = password
            isProgramming = true
            binding.statusText.text = "Tap an NFC card to program..."
            binding.programButton.isEnabled = false
        }
        
        binding.backButton.setOnClickListener {
            finish()
        }
        
        // Check NFC availability
        if (nfcAdapter == null) {
            showError("NFC is not available on this device")
            return
        }
        
        if (!nfcAdapter.isEnabled) {
            showError("NFC is disabled. Please enable it in settings")
            return
        }
    }
    
    private fun setupNFC() {
        if (nfcAdapter == null) return
        
        val intent = Intent(this, javaClass).apply {
            addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        
        pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_MUTABLE
        )
    }
    
    override fun onResume() {
        super.onResume()
        if (nfcAdapter != null && nfcAdapter.isEnabled) {
            enableNfcForegroundDispatch()
        }
    }
    
    override fun onPause() {
        super.onPause()
        if (nfcAdapter != null) {
            disableNfcForegroundDispatch()
        }
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        
        if (NfcAdapter.ACTION_TECH_DISCOVERED == intent.action) {
            val tag = intent.getParcelableExtra<Tag>(NfcAdapter.EXTRA_TAG)
            tag?.let { handleNFCTag(it) }
        }
    }
    
    private fun handleNFCTag(tag: Tag) {
        if (!isProgramming) return
        
        if (!nfcManager.isNTAG214(tag)) {
            showError("Unsupported NFC tag type. Please use NTAG214")
            resetProgramming()
            return
        }
        
        binding.statusText.text = "Programming card..."
        
        lifecycleScope.launch {
            try {
                val uid = nfcManager.readUID(tag)
                
                // Set password on the card (12345678)
                val success = nfcManager.setPassword(tag)
                
                if (success) {
                    // Register card with server (just UID needed now)
                    val card = NFCCard(uid, "", "")
                    val authToken = getAuthToken()
                    
                    val registerResult = networkManager.registerCard(card, authToken)
                    
                    registerResult.fold(
                        onSuccess = { registered ->
                            if (registered) {
                                showSuccess("Card programmed successfully!")
                                audioManager.playSuccessSound()
                            } else {
                                showError("Card programmed but server registration failed")
                                audioManager.playFailureSound()
                            }
                        },
                        onFailure = { exception ->
                            showError("Card programmed but server error: ${exception.message}")
                            audioManager.playFailureSound()
                        }
                    )
                } else {
                    showError("Failed to set password on card")
                    audioManager.playFailureSound()
                }
                
            } catch (e: Exception) {
                showError("Programming error: ${e.message}")
                audioManager.playFailureSound()
            }
            
            resetProgramming()
        }
    }
    
    private fun resetProgramming() {
        isProgramming = false
        binding.programButton.isEnabled = true
        binding.passwordEditText.text?.clear()
        currentPassword = ""
    }
    
    private fun enableNfcForegroundDispatch() {
        val intentFilter = IntentFilter(NfcAdapter.ACTION_TECH_DISCOVERED)
        val techList = arrayOf(arrayOf("android.nfc.tech.NfcA"))
        
        nfcAdapter.enableForegroundDispatch(this, pendingIntent, arrayOf(intentFilter), techList)
    }
    
    private fun disableNfcForegroundDispatch() {
        nfcAdapter.disableForegroundDispatch(this)
    }
    
    private fun showSuccess(message: String) {
        binding.statusText.text = message
        binding.statusText.setTextColor(getColor(R.color.success_green))
    }
    
    private fun showError(message: String) {
        binding.statusText.text = message
        binding.statusText.setTextColor(getColor(R.color.error_red))
    }
    
    private fun getAuthToken(): String {
        val prefs = getSharedPreferences("app_prefs", MODE_PRIVATE)
        return prefs.getString("auth_token", "") ?: ""
    }
    
    override fun onDestroy() {
        super.onDestroy()
        audioManager.cleanup()
    }
}

