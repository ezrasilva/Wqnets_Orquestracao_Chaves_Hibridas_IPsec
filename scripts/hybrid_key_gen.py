import hashlib
import hmac
import secrets
import json

try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    HAS_CHACHA20 = True
except ImportError:
    HAS_CHACHA20 = False

def hkdf_extract(salt, input_key_material):
    """
    HKDF-Extract: Extrai uma chave pseudo-aleatória (PRK) do material de entrada.
    """
    
    return hmac.new(salt, input_key_material, hashlib.sha256).digest()

def hkdf_expand(pseudo_random_key, info, length=32):
    """
    HKDF-Expand: Expande a PRK para uma chave do tamanho desejado.
    """
    t = b""
    okm = b""
    i = 0
    while len(okm) < length:
        i += 1
        t = hmac.new(pseudo_random_key, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
    return okm[:length]

def mix_keys(pqc_secret, qkd_key):
    """
    MODO HÍBRIDO: Combina a chave PQC (Kyber) e a chave QKD usando HKDF-SHA256.
    Retorna uma chave de 32 bytes (256 bits) pronta para o AES.
    """

    input_key_material = pqc_secret + qkd_key
    salt = secrets.token_bytes(32) 
    
    prk = hkdf_extract(salt, input_key_material)
    
    final_key = hkdf_expand(prk, b"SDQC-HYBRID-KEY", 32)
    
    return final_key

def hkdf_pqc_only(pqc_secret):
    """
    MODO PQC-ONLY: Usa apenas o segredo PQC com HKDF, sem zero artificial.
    Quando QKD não está disponível, gera chave apenas de PQC + label específico.
    Retorna uma chave de 32 bytes (256 bits) pronta para o AES.
    """
    
    salt = secrets.token_bytes(32)
    
    prk = hkdf_extract(salt, pqc_secret)
    
    final_key = hkdf_expand(prk, b"SDQC-PQC-ONLY", 32)
    
    return final_key

def derive_aead_key(shared_secret, context_label):
    """
    Deriva uma chave AEAD (32 bytes) a partir do shared_secret usando HKDF.
    A derivacao precisa ser deterministica para que emissor e receptor
    obtenham exatamente a mesma chave para o mesmo shared_secret.
    """
    label_bytes = context_label.encode("utf-8")
    salt = hashlib.sha256(b"SDQC-AEAD-SALT|" + label_bytes).digest()
    prk = hkdf_extract(salt, shared_secret)
    aead_key = hkdf_expand(prk, b"SDQC-AEAD-KEY|" + label_bytes, 32)
    return aead_key

def encrypt_payload_aead(payload_dict, aead_key):
    """
    Criptografa payload JSON com ChaCha20-Poly1305 (AEAD).
    O AAD é um valor fixo para garantir que o contexto seja validado.
    
    Retorna: {
        'ciphertext': bytes,
        'nonce': bytes (12 bytes),
        'tag': bytes (16 bytes - incluído no ciphertext)
    }
    """
    if not HAS_CHACHA20:
        raise ImportError("cryptography library required for ChaCha20-Poly1305")
    
    # Serializar payload
    payload_json = json.dumps(payload_dict)
    payload_bytes = payload_json.encode('utf-8')
    
    # Gerar nonce aleatório (12 bytes para ChaCha20-Poly1305)
    nonce = secrets.token_bytes(12)
    
    # AAD: informação fixa para garantir contexto de aplicação
    # Isso garante que a criptografia só pode ser verificada neste contexto
    aad_bytes = b"SDQC-control-message"
    
    # Criptografar
    cipher = ChaCha20Poly1305(aead_key)
    ciphertext = cipher.encrypt(nonce, payload_bytes, aad_bytes)
    
    return {
        'ciphertext': ciphertext,  # Inclui tag de autenticação
        'nonce': nonce
    }

def decrypt_payload_aead(ciphertext, nonce, aead_key):
    """
    Descriptografa payload com ChaCha20-Poly1305 (AEAD).
    Valida integrity/authenticity contra AAD (associated data).
    
    Args:
        ciphertext: bytes (inclui 16-byte authentication tag)
        nonce: bytes (12 bytes)
        aead_key: bytes (32 bytes)
    
    Retorna: payload_dict descriptografado e verificado
    """
    if not HAS_CHACHA20:
        raise ImportError("cryptography library required for ChaCha20-Poly1305")
    
    # AAD: mesmo valor fixo usado na criptografia
    aad_bytes = b"SDQC-control-message"
    
    # Descriptografar e verificar autenticidade
    cipher = ChaCha20Poly1305(aead_key)
    plaintext = cipher.decrypt(nonce, ciphertext, aad_bytes)
    
    # Parser JSON
    payload_dict = json.loads(plaintext.decode('utf-8'))
    
    return payload_dict