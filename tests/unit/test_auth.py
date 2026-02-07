"""单元测试 - 认证功能"""
import pytest
import base64
import hashlib
import hmac
from app import (
    _validate_username,
    _validate_password,
    _hash_password,
    _verify_password,
    _generate_api_key,
    User,
    USERNAME_PATTERN,
    PASSWORD_PATTERN,
)


class TestUsernameValidation:
    """用户名验证测试"""
    
    def test_valid_usernames(self):
        """测试有效用户名"""
        valid_names = ["user123", "test_user", "User_01", "abcd", "a" * 20]
        for name in valid_names:
            assert _validate_username(name) == True, f"{name} 应该有效"
    
    def test_invalid_usernames_too_short(self):
        """测试用户名过短"""
        assert _validate_username("ab") == False
        assert _validate_username("abc") == False
    
    def test_invalid_usernames_too_long(self):
        """测试用户名过长"""
        assert _validate_username("a" * 21) == False
        assert _validate_username("a" * 50) == False
    
    def test_invalid_usernames_special_chars(self):
        """测试包含特殊字符的用户名"""
        invalid_names = ["user@123", "test-user", "user.name", "user 123", "test!user"]
        for name in invalid_names:
            assert _validate_username(name) == False, f"{name} 应该无效"
    
    def test_invalid_usernames_empty(self):
        """测试空用户名"""
        assert _validate_username("") == False
        assert _validate_username("   ") == False


class TestPasswordValidation:
    """密码验证测试"""
    
    def test_valid_passwords(self):
        """测试有效密码"""
        valid_passwords = ["Pass1234", "HelloWorld1", "Test12345", "aB1" * 3 + "cdef"]
        for pwd in valid_passwords:
            assert _validate_password(pwd) == True, f"{pwd} 应该有效"
    
    def test_invalid_passwords_too_short(self):
        """测试密码过短"""
        assert _validate_password("Abc123") == False  # 6 chars
        assert _validate_password("Test12") == False  # 6 chars
    
    def test_invalid_passwords_no_letters(self):
        """测试纯数字密码"""
        assert _validate_password("12345678") == False
        assert _validate_password("1234567890") == False
    
    def test_invalid_passwords_no_numbers(self):
        """测试纯字母密码"""
        assert _validate_password("onlyletters") == False
        assert _validate_password("Password") == False
    
    def test_invalid_passwords_empty(self):
        """测试空密码"""
        assert _validate_password("") == False


class TestPasswordHashing:
    """密码哈希测试"""
    
    def test_hash_password_returns_tuple(self):
        """测试哈希函数返回盐和哈希值"""
        salt, digest = _hash_password("TestPassword123")
        assert len(salt) == 16
        assert len(digest) == 32  # SHA256 produces 32 bytes
    
    def test_hash_password_different_salts(self):
        """测试相同密码产生不同哈希"""
        salt1, hash1 = _hash_password("TestPassword123")
        salt2, hash2 = _hash_password("TestPassword123")
        assert salt1 != salt2
        assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """测试正确密码验证"""
        salt, hash_val = _hash_password("TestPassword123")
        user = User(
            username="testuser",
            api_key="test_key",
            password_salt=salt,
            password_hash=hash_val,
            iterations=260000
        )
        assert _verify_password(user, "TestPassword123") == True
    
    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        salt, hash_val = _hash_password("TestPassword123")
        user = User(
            username="testuser",
            api_key="test_key",
            password_salt=salt,
            password_hash=hash_val,
            iterations=260000
        )
        assert _verify_password(user, "WrongPassword") == False
        assert _verify_password(user, "") == False


class TestApiKeyGeneration:
    """API Key生成测试"""
    
    def test_generate_api_key_format(self):
        """测试API Key格式"""
        api_key = _generate_api_key()
        assert api_key.startswith("cs_")
        assert len(api_key) > 10
    
    def test_generate_api_key_unique(self):
        """测试生成的API Key唯一性"""
        keys = [_generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100, "生成的API Key应该唯一"


class TestRegexPatterns:
    """正则表达式测试"""
    
    def test_username_pattern(self):
        """测试用户名正则"""
        assert USERNAME_PATTERN.match("user123")
        assert USERNAME_PATTERN.match("test_user")
        assert not USERNAME_PATTERN.match("ab")  # too short
        assert not USERNAME_PATTERN.match("user@123")  # invalid char
    
    def test_password_pattern(self):
        """测试密码正则"""
        assert PASSWORD_PATTERN.match("Pass1234")
        assert not PASSWORD_PATTERN.match("onlyletters")  # no numbers
        assert not PASSWORD_PATTERN.match("12345678")  # no letters
