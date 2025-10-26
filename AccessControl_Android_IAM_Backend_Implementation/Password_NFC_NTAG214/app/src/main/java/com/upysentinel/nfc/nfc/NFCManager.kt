package com.upysentinel.nfc.nfc

import android.nfc.Tag
import android.nfc.tech.NfcA
import com.upysentinel.nfc.data.model.SecurityUtils
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.IOException

/**
 * NFC Manager for handling NTAG214 operations
 */
class NFCManager {
    
    companion object {
        private const val PAGE_SIZE = 4
        private const val USER_MEMORY_START = 4
        private const val MAX_USER_PAGES = 36
        private const val HASH_PAGE = 4
        private const val SALT_PAGE = 5
        private const val READ_COMMAND = 0x30.toByte()
        private const val WRITE_COMMAND = 0xA2.toByte()
        private const val PWD_AUTH_COMMAND = 0x1B.toByte()
        
        // Default password: 12345678 in hex
        private val DEFAULT_PASSWORD = byteArrayOf(0x12, 0x34, 0x56, 0x78)
    }
    
    /**
     * Read UID from NFC tag
     */
    fun readUID(tag: Tag): String {
        return SecurityUtils.bytesToHex(tag.id)
    }
    
    /**
     * Validate card password using PWD_AUTH command (0x1B)
     * Returns true if password is correct, false otherwise
     */
    suspend fun validatePassword(tag: Tag, password: ByteArray = DEFAULT_PASSWORD): Boolean = withContext(Dispatchers.IO) {
        val nfcA = NfcA.get(tag)
        try {
            nfcA.connect()
            
            // Build PWD_AUTH command: 0x1B + 4 bytes password
            val command = ByteArray(5)
            command[0] = PWD_AUTH_COMMAND
            System.arraycopy(password, 0, command, 1, 4)
            
            // Send authentication command
            val response = nfcA.transceive(command)
            
            // Success response is PACK (2 bytes) + ACK (0x0A)
            // If authentication fails, tag will return NACK or throw exception
            response.isNotEmpty() && response.size >= 2
            
        } catch (e: Exception) {
            // Authentication failed or communication error
            false
        } finally {
            try {
                nfcA.close()
            } catch (e: IOException) {
                // Ignore close errors
            }
        }
    }
    
    /**
     * Read hash from NTAG214 memory
     */
    suspend fun readHash(tag: Tag): String? = withContext(Dispatchers.IO) {
        val nfcA = NfcA.get(tag)
        try {
            nfcA.connect()
            val hashBytes = readMultiplePages(nfcA, HASH_PAGE, 8)
            if (hashBytes != null) {
                String(hashBytes).trimEnd('\u0000')
            } else null
        } catch (e: Exception) {
            null
        } finally {
            try {
                nfcA.close()
            } catch (e: IOException) {
                // Ignore close errors
            }
        }
    }
    
    /**
     * Read salt from NTAG214 memory
     */
    suspend fun readSalt(tag: Tag): String? = withContext(Dispatchers.IO) {
        val nfcA = NfcA.get(tag)
        try {
            nfcA.connect()
            val saltBytes = readMultiplePages(nfcA, SALT_PAGE + 8, 4)
            if (saltBytes != null) {
                String(saltBytes).trimEnd('\u0000')
            } else null
        } catch (e: Exception) {
            null
        } finally {
            try {
                nfcA.close()
            } catch (e: IOException) {
                // Ignore close errors
            }
        }
    }
    
    /**
     * Read hash and salt from NTAG214 memory
     */
    suspend fun readCardData(tag: Tag): Pair<String?, String?> = withContext(Dispatchers.IO) {
        val nfcA = NfcA.get(tag)
        try {
            nfcA.connect()
            
            // Read hash (32 bytes = 8 pages starting from page 4)
            val hashBytes = readMultiplePages(nfcA, HASH_PAGE, 8)
            val hash = if (hashBytes != null) {
                String(hashBytes).trimEnd('\u0000')
            } else null
            
            // Read salt (16 bytes = 4 pages starting from page 12)
            val saltBytes = readMultiplePages(nfcA, SALT_PAGE + 8, 4)
            val salt = if (saltBytes != null) {
                String(saltBytes).trimEnd('\u0000')
            } else null
            
            Pair(hash, salt)
        } catch (e: Exception) {
            Pair(null, null)
        } finally {
            try {
                nfcA.close()
            } catch (e: IOException) {
                // Ignore close errors
            }
        }
    }
    
    /**
     * Write hash and salt to NTAG214 memory
     */
    suspend fun writeCardData(tag: Tag, hash: String, salt: String): Boolean = withContext(Dispatchers.IO) {
        val nfcA = NfcA.get(tag)
        try {
            nfcA.connect()
            
            // Write hash (32 bytes = 8 pages)
            val hashBytes = hash.padEnd(32, '\u0000').toByteArray()
            val hashSuccess = writeMultiplePages(nfcA, HASH_PAGE, hashBytes)
            
            // Write salt (16 bytes = 4 pages)
            val saltBytes = salt.padEnd(16, '\u0000').toByteArray()
            val saltSuccess = writeMultiplePages(nfcA, SALT_PAGE + 8, saltBytes)
            
            hashSuccess && saltSuccess
        } catch (e: Exception) {
            false
        } finally {
            try {
                nfcA.close()
            } catch (e: IOException) {
                // Ignore close errors
            }
        }
    }
    
    /**
     * Read multiple pages from NTAG214
     */
    private fun readMultiplePages(nfcA: NfcA, startPage: Int, pageCount: Int): ByteArray? {
        try {
            val totalBytes = pageCount * PAGE_SIZE
            val result = ByteArray(totalBytes)
            var offset = 0
            
            for (i in 0 until pageCount) {
                val page = startPage + i
                val command = byteArrayOf(READ_COMMAND, page.toByte())
                val response = nfcA.transceive(command)
                
                if (response.size >= PAGE_SIZE) {
                    System.arraycopy(response, 0, result, offset, PAGE_SIZE)
                    offset += PAGE_SIZE
                } else {
                    return null
                }
            }
            
            return result
        } catch (e: Exception) {
            return null
        }
    }
    
    /**
     * Write multiple pages to NTAG214
     */
    private fun writeMultiplePages(nfcA: NfcA, startPage: Int, data: ByteArray): Boolean {
        try {
            val pageCount = data.size / PAGE_SIZE
            
            for (i in 0 until pageCount) {
                val page = startPage + i
                val pageData = ByteArray(PAGE_SIZE)
                System.arraycopy(data, i * PAGE_SIZE, pageData, 0, PAGE_SIZE)
                
                val command = ByteArray(6)
                command[0] = WRITE_COMMAND
                command[1] = page.toByte()
                System.arraycopy(pageData, 0, command, 2, PAGE_SIZE)
                
                val response = nfcA.transceive(command)
                if (response.size < 1 || response[0] != 0x0A.toByte()) {
                    return false
                }
            }
            
            return true
        } catch (e: Exception) {
            return false
        }
    }
    
    /**
     * Set password on NTAG214 card
     * Password is written to pages 0xE5-0xE6 (PWD and PACK)
     */
    suspend fun setPassword(tag: Tag, password: ByteArray = DEFAULT_PASSWORD): Boolean = withContext(Dispatchers.IO) {
        val nfcA = NfcA.get(tag)
        try {
            nfcA.connect()
            
            // Write password to page 0xE5 (229)
            val pwdCommand = ByteArray(6)
            pwdCommand[0] = WRITE_COMMAND
            pwdCommand[1] = 0xE5.toByte()
            System.arraycopy(password, 0, pwdCommand, 2, 4)
            
            val pwdResponse = nfcA.transceive(pwdCommand)
            if (pwdResponse.size < 1 || pwdResponse[0] != 0x0A.toByte()) {
                return@withContext false
            }
            
            // Write PACK (password acknowledge) to page 0xE6 (230)
            // Using default PACK: 0x00 0x00
            val packCommand = ByteArray(6)
            packCommand[0] = WRITE_COMMAND
            packCommand[1] = 0xE6.toByte()
            packCommand[2] = 0x00
            packCommand[3] = 0x00
            packCommand[4] = 0x00
            packCommand[5] = 0x00
            
            val packResponse = nfcA.transceive(packCommand)
            packResponse.size >= 1 && packResponse[0] == 0x0A.toByte()
            
        } catch (e: Exception) {
            false
        } finally {
            try {
                nfcA.close()
            } catch (e: IOException) {
                // Ignore close errors
            }
        }
    }
    
    /**
     * Check if tag is NTAG214 compatible
     */
    fun isNTAG214(tag: Tag): Boolean {
        val techList = tag.techList
        return techList.contains("android.nfc.tech.NfcA")
    }
    
    /**
     * Get tag information
     */
    fun getTagInfo(tag: Tag): TagInfo {
        val uid = readUID(tag)
        val techList = tag.techList.toList()
        val isCompatible = isNTAG214(tag)
        
        return TagInfo(
            uid = uid,
            techList = techList,
            isNTAG214 = isCompatible
        )
    }
}

/**
 * Data class for tag information
 */
data class TagInfo(
    val uid: String,
    val techList: List<String>,
    val isNTAG214: Boolean
)
