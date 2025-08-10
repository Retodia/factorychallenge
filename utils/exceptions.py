"""Custom exceptions for Challenge Factory application"""

class ChallengeFactoryException(Exception):
    """Base exception for Challenge Factory"""
    pass

class FirestoreException(ChallengeFactoryException):
    """Firestore operation exceptions"""
    pass

class VertexAIException(ChallengeFactoryException):
    """Vertex AI operation exceptions"""
    pass

class StorageException(ChallengeFactoryException):
    """Cloud Storage operation exceptions"""
    pass

class TTSException(ChallengeFactoryException):
    """Text-to-Speech operation exceptions"""
    pass

class ImageGenerationException(ChallengeFactoryException):
    """Image generation operation exceptions"""
    pass

class UserDataException(ChallengeFactoryException):
    """User data related exceptions"""
    pass

class PromptFileException(ChallengeFactoryException):
    """Prompt file operation exceptions"""
    pass

class ValidationException(ChallengeFactoryException):
    """Data validation exceptions"""
    pass