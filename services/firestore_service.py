import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from config.settings import settings

logger = logging.getLogger(__name__)

class FirestoreService:
    """Service for Firestore operations"""
    
    def __init__(self):
        self.db = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            try:
                firebase_admin.get_app()
                logger.info("Firebase already initialized")
            except ValueError:
                # Initialize Firebase
                if settings.GOOGLE_APPLICATION_CREDENTIALS:
                    cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
                    firebase_admin.initialize_app(cred, {
                        'projectId': settings.PROJECT_ID
                    })
                else:
                    # Use default credentials in Cloud Run
                    firebase_admin.initialize_app()
                logger.info("Firebase initialized successfully")
            
            self.db = firestore.client()
            
        except Exception as e:
            logger.error(f"Error initializing Firebase: {str(e)}")
            raise
    
    async def get_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get all user data needed for prompt generation
        Returns: Combined data from users, infouser, and avances collections
        """
        try:
            user_data = {}
            
            # Get user basic info (nombre, d1, d2, d3, d4)
            user_doc = self.db.collection(settings.COLLECTION_USERS).document(user_id).get()
            if user_doc.exists:
                user_data.update(user_doc.to_dict())
            else:
                logger.warning(f"User {user_id} not found in users collection")
                return {}
            
            # Get additional user info
            infouser_doc = self.db.collection(settings.COLLECTION_INFOUSER).document(user_id).get()
            if infouser_doc.exists:
                user_data.update(infouser_doc.to_dict())
            
            # Get latest avances (progress)
            avances_query = (
                self.db.collection(settings.COLLECTION_AVANCES)
                .where(filter=FieldFilter("userid", "==", user_id))
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(5)
            )
            
            avances_docs = avances_query.stream()
            avances_list = []
            for doc in avances_docs:
                avance_data = doc.to_dict()
                avances_list.append(avance_data.get('texto', ''))
            
            user_data['avances'] = avances_list
            user_data['userid'] = user_id
            
            logger.info(f"Retrieved data for user {user_id}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error getting user data for {user_id}: {str(e)}")
            raise
    
    async def get_all_active_users(self) -> List[str]:
        """Get all active user IDs"""
        try:
            users_ref = self.db.collection(settings.COLLECTION_USERS)
            docs = users_ref.stream()
            
            user_ids = []
            for doc in docs:
                user_data = doc.to_dict()
                # Add logic here to filter active users if needed
                # For now, include all users
                user_ids.append(doc.id)
            
            logger.info(f"Found {len(user_ids)} active users")
            return user_ids
            
        except Exception as e:
            logger.error(f"Error getting active users: {str(e)}")
            raise
    
    async def create_reto_diario(self, user_id: str, brief: str) -> str:
        """
        Create a new daily challenge entry
        Returns: Document ID
        """
        try:
            reto_data = {
                'userid': user_id,
                'brief': brief,
                'fecha': datetime.now().isoformat(),
                'timestamp': firestore.SERVER_TIMESTAMP,
                'retodia': '',
                'retoimagen': '',
                'retopodcast': ''
            }
            
            doc_ref = self.db.collection(settings.COLLECTION_RETOS).add(reto_data)
            doc_id = doc_ref[1].id
            
            logger.info(f"Created reto diario {doc_id} for user {user_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error creating reto diario: {str(e)}")
            raise
    
    async def update_reto_diario(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """Update a reto diario document"""
        try:
            doc_ref = self.db.collection(settings.COLLECTION_RETOS).document(doc_id)
            doc_ref.update(updates)
            
            logger.info(f"Updated reto diario {doc_id} with fields: {list(updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating reto diario {doc_id}: {str(e)}")
            raise
    
    async def get_reto_diario(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific reto diario document"""
        try:
            doc_ref = self.db.collection(settings.COLLECTION_RETOS).document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"Reto diario {doc_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting reto diario {doc_id}: {str(e)}")
            raise
    
    async def get_latest_reto_with_brief(self, user_id: str) -> Optional[tuple]:
        """
        Get the latest reto diario that has a brief but missing other fields
        Returns: (doc_id, reto_data) or None
        """
        try:
            query = (
                self.db.collection(settings.COLLECTION_RETOS)
                .where(filter=FieldFilter("userid", "==", user_id))
                .where(filter=FieldFilter("brief", "!=", ""))
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(1)
            )
            
            docs = list(query.stream())
            
            if docs:
                doc = docs[0]
                reto_data = doc.to_dict()
                
                # Check if other fields are still empty
                if (not reto_data.get('retodia') or 
                    not reto_data.get('retoimagen') or 
                    not reto_data.get('retopodcast')):
                    return doc.id, reto_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest reto for user {user_id}: {str(e)}")
            raise