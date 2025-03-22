import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def format_text(text: str, format_type: str) -> Dict[str, Any]:
    """
    Format text according to the specified format type.
    
    Args:
        text: The text to format
        format_type: Type of formatting to apply (upper, lower, title, capitalize)
        
    Returns:
        Dictionary with the formatted text
    """
    logger.info(f"Formatting text with format_type: {format_type}")
    
    try:
        if format_type == "upper":
            result = text.upper()
        elif format_type == "lower":
            result = text.lower()
        elif format_type == "title":
            result = text.title()
        elif format_type == "capitalize":
            result = text.capitalize()
        else:
            return {"error": f"Unsupported format type: {format_type}"}
            
        return {"formatted_text": result}
        
    except Exception as e:
        logger.error(f"Error formatting text: {str(e)}")
        return {"error": f"Error formatting text: {str(e)}"}

async def count_words(text: str) -> Dict[str, Any]:
    """
    Count the number of words in the text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Dictionary with word count statistics
    """
    logger.info(f"Counting words in text of length: {len(text)}")
    
    try:
        # Split the text and count words
        words = text.split()
        word_count = len(words)
        
        # Count unique words
        unique_words = len(set(words))
        
        # Find longest and shortest words
        if words:
            longest_word = max(words, key=len)
            shortest_word = min(words, key=len)
        else:
            longest_word = ""
            shortest_word = ""
            
        return {
            "total_words": word_count,
            "unique_words": unique_words,
            "longest_word": longest_word,
            "shortest_word": shortest_word,
            "average_word_length": sum(len(word) for word in words) / max(word_count, 1)
        }
        
    except Exception as e:
        logger.error(f"Error counting words: {str(e)}")
        return {"error": f"Error counting words: {str(e)}"} 