import logging
from typing import Dict, Any
import vertexai
from vertexai.generative_models import GenerativeModel
from config.settings import settings

logger = logging.getLogger(__name__)

class VertexAIService:
    """Service for Vertex AI Gemini operations"""
    
    def __init__(self):
        self.model = None
        self._initialize_vertex_ai()
    
    def _initialize_vertex_ai(self):
        """Initialize Vertex AI"""
        try:
            vertexai.init(
                project=settings.PROJECT_ID,
                location=settings.VERTEX_AI_LOCATION
            )
            
            # Use the correct model name for the current API
            self.model = GenerativeModel("gemini-1.5-pro")
            logger.info("Vertex AI initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Vertex AI: {str(e)}")
            raise
    
    def _load_prompt_template(self, prompt_file: str) -> str:
        """Load prompt template from file"""
        try:
            from config.settings import get_prompt_file_path
            prompt_path = get_prompt_file_path(prompt_file)
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            return template
            
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_file}")
            return f"Error: Prompt file {prompt_file} not found. Please create the file."
        except Exception as e:
            logger.error(f"Error loading prompt {prompt_file}: {str(e)}")
            raise
    
    def _replace_variables_in_prompt(self, template: str, user_data: Dict[str, Any]) -> str:
        """Replace variables in prompt template with user data"""
        try:
            # Replace common variables
            prompt = template.replace("{nombre}", user_data.get('nombre', 'Usuario'))
            prompt = prompt.replace("{d1}", user_data.get('d1', ''))
            prompt = prompt.replace("{d2}", user_data.get('d2', ''))
            prompt = prompt.replace("{d3}", user_data.get('d3', ''))
            prompt = prompt.replace("{d4}", user_data.get('d4', ''))
            prompt = prompt.replace("{userid}", user_data.get('userid', ''))
            
            # Handle avances (progress) - join recent progress
            avances = user_data.get('avances', [])
            avances_text = " ".join(avances[:3]) if avances else "No hay avances registrados"
            prompt = prompt.replace("{avances}", avances_text)
            
            # Add current date
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            prompt = prompt.replace("{fecha}", today)
            
            # Handle brief for subsequent prompts
            if 'brief' in user_data:
                prompt = prompt.replace("{brief}", user_data.get('brief', ''))
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error replacing variables in prompt: {str(e)}")
            return template
    
    async def generate_brief(self, user_data: Dict[str, Any]) -> str:
        """Generate brief using prompt1"""
        try:
            template = self._load_prompt_template(settings.PROMPT1_FILE)
            prompt = self._replace_variables_in_prompt(template, user_data)
            
            logger.info(f"Generating brief for user {user_data.get('userid')}")
            
            response = self.model.generate_content(prompt)
            brief = response.text.strip()
            
            logger.info(f"Brief generated successfully for user {user_data.get('userid')}")
            return brief
            
        except Exception as e:
            logger.error(f"Error generating brief: {str(e)}")
            # Return a fallback response instead of raising
            return f"Error generating brief: {str(e)}"
    
    async def generate_reto_dia(self, user_data: Dict[str, Any]) -> str:
        """Generate daily challenge using prompt_retodia"""
        try:
            template = self._load_prompt_template(settings.PROMPT_RETODIA_FILE)
            prompt = self._replace_variables_in_prompt(template, user_data)
            
            logger.info(f"Generating reto dia for user {user_data.get('userid')}")
            
            response = self.model.generate_content(prompt)
            reto_dia = response.text.strip()
            
            logger.info(f"Reto dia generated successfully for user {user_data.get('userid')}")
            return reto_dia
            
        except Exception as e:
            logger.error(f"Error generating reto dia: {str(e)}")
            return f"Error generating reto dia: {str(e)}"
    
    async def generate_imagen_prompt(self, user_data: Dict[str, Any]) -> str:
        """Generate image description using prompt_imagen"""
        try:
            template = self._load_prompt_template(settings.PROMPT_IMAGEN_FILE)
            prompt = self._replace_variables_in_prompt(template, user_data)
            
            logger.info(f"Generating imagen prompt for user {user_data.get('userid')}")
            
            response = self.model.generate_content(prompt)
            imagen_prompt = response.text.strip()
            
            logger.info(f"Imagen prompt generated successfully for user {user_data.get('userid')}")
            return imagen_prompt
            
        except Exception as e:
            logger.error(f"Error generating imagen prompt: {str(e)}")
            return f"Error generating imagen prompt: {str(e)}"
    
    async def generate_podcast_script(self, user_data: Dict[str, Any]) -> str:
        """Generate podcast script using prompt_podcast"""
        try:
            template = self._load_prompt_template(settings.PROMPT_PODCAST_FILE)
            prompt = self._replace_variables_in_prompt(template, user_data)
            
            logger.info(f"Generating podcast script for user {user_data.get('userid')}")
            
            response = self.model.generate_content(prompt)
            podcast_script = response.text.strip()
            
            logger.info(f"Podcast script generated successfully for user {user_data.get('userid')}")
            return podcast_script
            
        except Exception as e:
            logger.error(f"Error generating podcast script: {str(e)}")
            return f"Error generating podcast script: {str(e)}"
