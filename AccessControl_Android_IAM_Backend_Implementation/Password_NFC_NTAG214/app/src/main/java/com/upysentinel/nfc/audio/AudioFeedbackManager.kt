package com.upysentinel.nfc.audio

import android.content.Context
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.ToneGenerator
import kotlinx.coroutines.*

/**
 * Audio feedback manager for NFC access control
 */
class AudioFeedbackManager(private val context: Context) {
    
    private var toneGenerator: ToneGenerator? = null
    private var alarmPlayer: MediaPlayer? = null
    private var failureCount = 0
    private var firstFailureTime = 0L
    private val failureWindow = 60000L // 1 minute in milliseconds
    private var isAlarmActive = false
    private var alarmJob: Job? = null
    
    init {
        initializeToneGenerator()
    }
    
    private fun initializeToneGenerator() {
        try {
            toneGenerator = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 100)
            android.util.Log.d("AudioFeedbackManager", "ToneGenerator initialized successfully")
        } catch (e: Exception) {
            android.util.Log.e("AudioFeedbackManager", "Failed to initialize ToneGenerator: ${e.message}")
            // Try with different stream type
            try {
                toneGenerator = ToneGenerator(AudioManager.STREAM_ALARM, 100)
                android.util.Log.d("AudioFeedbackManager", "ToneGenerator initialized with STREAM_ALARM")
            } catch (e2: Exception) {
                android.util.Log.e("AudioFeedbackManager", "Failed to initialize ToneGenerator with STREAM_ALARM: ${e2.message}")
            }
        }
    }
    
    /**
     * Play success sound (1-2 seconds)
     */
    fun playSuccessSound() {
        try {
            toneGenerator?.startTone(ToneGenerator.TONE_PROP_ACK, 1500) // 1.5 seconds
        } catch (e: Exception) {
            // Handle audio error
        }
    }
    
    /**
     * Play failure sound (1-2 seconds)
     */
    fun playFailureSound() {
        try {
            toneGenerator?.startTone(ToneGenerator.TONE_PROP_NACK, 1500) // 1.5 seconds
        } catch (e: Exception) {
            // Handle audio error
        }
    }
    
    /**
     * Handle access attempt result
     */
    fun handleAccessAttempt(success: Boolean, onSecurityAlert: () -> Unit) {
        val currentTime = System.currentTimeMillis()
        
        android.util.Log.d("AudioFeedbackManager", "handleAccessAttempt: success=$success, currentCount=$failureCount")
        
        if (success) {
            // Reset failure tracking on success
            resetFailureTracking()
            playSuccessSound()
            android.util.Log.d("AudioFeedbackManager", "Success - reset failure tracking")
        } else {
            // Always increment failure count for debugging
            failureCount++
            
            // Set first failure time if this is the first failure
            if (failureCount == 1) {
                firstFailureTime = currentTime
                android.util.Log.d("AudioFeedbackManager", "First failure - count: $failureCount, time: $firstFailureTime")
            } else {
                val timeSinceFirstFailure = currentTime - firstFailureTime
                android.util.Log.d("AudioFeedbackManager", "Failure #$failureCount - time since first: ${timeSinceFirstFailure}ms")
                
                // Reset if more than 1 minute has passed
                if (timeSinceFirstFailure > failureWindow) {
                    android.util.Log.d("AudioFeedbackManager", "Window expired - resetting count")
                    failureCount = 1
                    firstFailureTime = currentTime
                }
            }
            
            playFailureSound()
            
            // Check if 3 failures in 1 minute
            if (failureCount >= 3 && !isAlarmActive) {
                android.util.Log.d("AudioFeedbackManager", "TRIGGERING ALARM - count: $failureCount")
                startPersistentAlarm()
                android.util.Log.d("AudioFeedbackManager", "Calling onSecurityAlert callback")
                onSecurityAlert()
                android.util.Log.d("AudioFeedbackManager", "onSecurityAlert callback completed")
            } else {
                android.util.Log.d("AudioFeedbackManager", "No alarm yet - count: $failureCount, alarm active: $isAlarmActive")
            }
        }
    }
    
    /**
     * Start persistent alarm sound (only stoppable from server)
     */
    fun startPersistentAlarm() {
        if (isAlarmActive) return // Already active
        
        isAlarmActive = true
        android.util.Log.d("AudioFeedbackManager", "Starting persistent alarm")
        
        try {
            // Cancel any existing alarm job first
            alarmJob?.cancel()
            
            // Start continuous alarm using coroutines
            alarmJob = CoroutineScope(Dispatchers.Main).launch {
                var toneCount = 0
                while (isAlarmActive) {
                    try {
                        toneCount++
                        android.util.Log.d("AudioFeedbackManager", "Playing alarm tone #$toneCount")
                        
                        // Try different alarm tones
                        val tone = when (toneCount % 3) {
                            0 -> ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD
                            1 -> ToneGenerator.TONE_CDMA_ALERT_NETWORK_LITE
                            2 -> ToneGenerator.TONE_CDMA_CONFIRM
                            else -> ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD
                        }
                        
                        toneGenerator?.startTone(tone, 2000)
                        delay(2500) // Wait 2.5 seconds between alarm sounds
                    } catch (e: Exception) {
                        android.util.Log.e("AudioFeedbackManager", "Error playing alarm tone: ${e.message}")
                        delay(1000)
                    }
                }
                android.util.Log.d("AudioFeedbackManager", "Alarm stopped")
            }
        } catch (e: Exception) {
            android.util.Log.e("AudioFeedbackManager", "Error starting alarm: ${e.message}")
        }
    }
    
    /**
     * Stop persistent alarm (only called from server)
     */
    fun stopAlarm() {
        isAlarmActive = false
        alarmJob?.cancel()
        alarmJob = null
        
        try {
            alarmPlayer?.apply {
                if (isPlaying) {
                    stop()
                }
                release()
            }
            alarmPlayer = null
        } catch (e: Exception) {
            // Handle stop error
        }
    }
    
    /**
     * Reset failure tracking
     */
    private fun resetFailureTracking() {
        failureCount = 0
        firstFailureTime = 0L
    }
    
    /**
     * Get current failure count
     */
    fun getFailureCount(): Int = failureCount
    
    /**
     * Check if alarm is active
     */
    fun isAlarmActive(): Boolean = isAlarmActive
    
    /**
     * Get time remaining in failure window (in milliseconds)
     */
    fun getTimeRemainingInWindow(): Long {
        if (failureCount == 0) return 0L
        val elapsed = System.currentTimeMillis() - firstFailureTime
        return maxOf(0L, failureWindow - elapsed)
    }
    
    /**
     * Cleanup resources
     */
    fun cleanup() {
        stopAlarm()
        toneGenerator?.release()
        toneGenerator = null
    }
}
