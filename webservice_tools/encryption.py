import base64
import os
from Crypto.Cipher import AES
ENCRYPTION_PADDING = ' '
ENCRYPTION_OBJECT_KEY = 'dbencryptionkey'


def encryptData(data):
    """
    Encrypts the data using the shared encryption key then returns it
    data: The data to encrypt, in plain-text format
    returns: The encrypted data, encoded in base64 format
    """
    encryptionObject = _getEncryptionObject()
    
    if not encryptionObject:
        return None

    if len(data) % AES.block_size != 0:
        dataBlockSize = len(data) / AES.block_size + 1
        data = str(data).rjust(dataBlockSize * AES.block_size, ENCRYPTION_PADDING)
    
    encryptedData = encryptionObject.encrypt(data)
    encodedData = base64.encodestring(encryptedData).rstrip('\n')

    return encodedData



def decryptData(data):
    """
    Decrypt and retrieve encrypted data
    data: The encryped data, passed in encoded in base64
    returns: Returns the data in plain-text format
    """
    encryptionObject = _getEncryptionObject()

    if not encryptionObject:
        return None
    
    decodedData = base64.decodestring(data)
    decryptedData = encryptionObject.decrypt(decodedData)
    return decryptedData.lstrip(ENCRYPTION_PADDING)


def _getEncryptionObject():
    """
    Gets the Encryption Object which is used to encrypt/decrypt data
    The encryption key is cached.
    """
    try:
        key = open('%s/dbkey' % os.getcwd()).read()
    except IOError:
        key = 'H3YY!H0pp3d0u70f7h47h0u$3w!7hmY>'
    return AES.new(key, AES.MODE_ECB)

