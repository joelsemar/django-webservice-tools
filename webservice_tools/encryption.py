import base64
from Crypto.Cipher import AES
from django.core.cache import cache
ENCRYPTION_PADDING = ' '
ENCRYPTION_OBJECT_KEY = 'dbencryptionkey'


def _getEncryptionObject():
    """
    Gets the Encryption Object which is used to encrypt/decrypt data
    The encryption key is cached.
    """
    from Crypto.Cipher import AES
    
    key = cache.get(ENCRYPTION_OBJECT_KEY)
    if key is None:
        import dbkey
        key = dbkey.key
        cache.set(ENCRYPTION_OBJECT_KEY, key)
    
    return AES.new(key, AES.MODE_ECB)


def decryptData(data):
    """
    Decrypt and retrieve encrypted data
    @param data: The encryped data, passed in encoded in base64
    @return: Returns the data in plain-text format
    """
    encryptionObject = _getEncryptionObject()

    if not encryptionObject:
        return None
    
    decodedData = base64.decodestring(data)
    decryptedData = encryptionObject.decrypt(decodedData)
    return decryptedData.lstrip(ENCRYPTION_PADDING)


def encryptData(data):
    """
    Encrypts the data using the shared encryption key then returns it
    @param data: The data to encrypt, in plain-text format
    @return: The encrypted data, encoded in base64 format
    """
    from Crypto.Cipher import AES
    encryptionObject = _getEncryptionObject()
    
    if not encryptionObject:
        return None

    if len(data) % AES.block_size != 0:
        dataBlockSize = len(data) / AES.block_size + 1
        data = str(data).rjust(dataBlockSize * AES.block_size, ENCRYPTION_PADDING)
    
    encryptedData = encryptionObject.encrypt(data)
    encodedData = base64.encodestring(encryptedData).rstrip('\n')
    return encodedData