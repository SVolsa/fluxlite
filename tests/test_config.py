import pytest
from fluxlite.config import encrypt_value, decrypt_value, save_config, load_config


class TestConfigEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        original = "sk-test-api-key-12345"
        encrypted = encrypt_value(original)
        assert encrypted != original
        assert encrypted.startswith("gA")
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_empty_string(self):
        assert encrypt_value("") == ""
        assert decrypt_value("") == ""

    def test_long_api_key(self):
        key = "sk-" + "a" * 100
        assert decrypt_value(encrypt_value(key)) == key

    def test_special_chars(self):
        key = "sk-!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        assert decrypt_value(encrypt_value(key)) == key

    def test_encrypt_idempotent(self):
        key = "sk-test-key"
        e1 = encrypt_value(key)
        e2 = encrypt_value(key)
        assert e1 != e2


class TestConfigSaveLoad:
    def test_save_and_load_config(self):
        config = {
            "api": {"key": "sk-secret", "base_url": "https://test.com", "model": "test-model"},
            "app": {"language": "en"},
        }
        save_config(config)
        loaded = load_config()
        assert loaded["api"]["key"] == "sk-secret"
        assert loaded["api"]["base_url"] == "https://test.com"
        assert loaded["app"]["language"] == "en"

    def test_config_file_encrypted(self):
        import fluxlite.config as cfg
        save_config({"api": {"key": "sk-secret", "base_url": "", "model": ""}})
        raw = open(cfg.CONFIG_PATH, "rb").read()
        assert b"sk-secret" not in raw

    def test_is_configured(self):
        from fluxlite.config import is_configured
        assert not is_configured()
        save_config({"api": {"key": "sk-key", "base_url": "", "model": ""}})
        assert is_configured()
