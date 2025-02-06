from openai import OpenAI
from typing import Dict, List, Optional
import json

class LLMServiceError(Exception):
    """Custom exception for LLM service errors"""
    pass

class LLMService:
    def __init__(self, base_url: str):
        try:
            self.client = OpenAI(base_url=base_url)
            self.model = "deepseek-r1-distill-llama-8b"
        except Exception as e:
            raise LLMServiceError(f"Failed to initialize LLM service: {str(e)}")

    def prepare_career_analysis_prompt(self, test_responses: Dict[str, List[Dict]]) -> str:
        """
        Prepares a detailed prompt for LLM with clear context and expectations
        """
        prompt = """As a career counseling expert, analyze the following assessment results and provide detailed career guidance. 
        The assessment consists of four key areas: Interests (TEST1), Strengths (TEST2), Personal Ambitions (TEST3), and Values (TEST4).

        Detailed Assessment Results:

        1. INTERESTS ASSESSMENT (How the person likes to work):
        {}

        2. STRENGTHS ASSESSMENT (What they're good at):
        {}

        3. PERSONAL AMBITIONS (Future goals and aspirations):
        {}

        4. PERSONAL VALUES (What matters most to them):
        {}

        Based on these comprehensive results, please provide:

        1. PRIMARY CAREER RECOMMENDATION:
        - Main career path that best aligns with their profile
        - Specific roles within this career path
        - Why this path suits their profile

        2. ALTERNATIVE CAREER PATHS:
        - At least 2 alternative career options
        - Reasoning for each alternative
        - How these align with different aspects of their profile

        3. KEY SKILLS TO DEVELOP:
        - Essential skills for the recommended career paths
        - Specific areas for improvement
        - Suggested learning resources or certifications

        4. ADDITIONAL INSIGHTS:
        - Unique strengths in their profile
        - Potential challenges to consider
        - Long-term career development opportunities

        Please structure your response clearly using these exact headings.
        """
        
        try:
            # Format each test's responses with additional context
            formatted_responses = []
            test_contexts = {
                'TEST1': "Interest Indicators",
                'TEST2': "Strength Indicators",
                'TEST3': "Ambition Indicators",
                'TEST4': "Value Indicators"
            }
            
            for test_num in range(1, 5):
                test_key = f'TEST{test_num}'
                responses = test_responses.get(test_key, [])
                
                if not responses:
                    raise LLMServiceError(f"Missing responses for {test_key}")
                
                test_responses_str = "\n".join([
                    f"- {resp['question']}: {'Yes' if resp['answer'] else 'No'} "
                    f"({test_contexts[test_key]})"
                    for resp in responses
                ])
                formatted_responses.append(test_responses_str)
            
            return prompt.format(*formatted_responses)
            
        except Exception as e:
            raise LLMServiceError(f"Error preparing prompt: {str(e)}")

    def parse_llm_response(self, response_text):
        """Parse the LLM response into structured sections."""
        try:
            sections = {
                'primary_recommendation': '',
                'alternative_paths': '',
                'skill_gaps': '',
                'additional_insights': ''
            }
            
            # Split the response into sections
            current_section = None
            lines = response_text.split('\n')
            
            for line in lines:
                if '1. PRIMARY CAREER RECOMMENDATION' in line:
                    current_section = 'primary_recommendation'
                    continue
                elif '2. ALTERNATIVE CAREER PATHS' in line:
                    current_section = 'alternative_paths'
                    continue
                elif '3. KEY SKILLS TO DEVELOP' in line:
                    current_section = 'skill_gaps'
                    continue
                elif '4. ADDITIONAL INSIGHTS' in line:
                    current_section = 'additional_insights'
                    continue
                
                if current_section and line.strip():
                    sections[current_section] += line + '\n'
            
            # Clean up the sections
            for key in sections:
                sections[key] = sections[key].strip()
            
            return sections
            
        except Exception as e:
            print(f"Error parsing LLM response: {str(e)}")
            print(f"Raw response: {response_text}")
            raise

    def get_career_analysis(self, test_responses: Dict[str, List[Dict]]) -> str:
        try:
            print("Preparing LLM prompt...")
            prompt = """Based on the test responses, provide a detailed career analysis following this structure:

            1. CAREER DIRECTION AND PRIMARY RECOMMENDATIONS
            - Analyze the key strengths and interests shown in the responses
            - Provide 2-3 specific career paths that best match their profile
            - For each career path, explain why it's a good fit based on their responses
            - Include specific roles or positions within these career paths

            2. SKILLS AND DEVELOPMENT ROADMAP
            - List the essential skills they already demonstrate
            - Identify specific skills they need to develop
            - Recommend concrete steps for skill development (e.g., specific courses, certifications, or training programs)
            - Suggest a timeline for skill acquisition

            3. EDUCATIONAL AND TRAINING RECOMMENDATIONS
            - Specific degree programs or certifications that align with their career paths
            - Online courses or bootcamps that would be beneficial
            - Professional certifications that would add value
            - Estimated time and resource investment for each recommendation

            4. PRACTICAL NEXT STEPS
            - Immediate actions they can take (within next 3 months)
            - Medium-term goals (6-12 months)
            - Long-term career development plan (2-5 years)
            - Specific companies or organizations to target

            5. ADDITIONAL INSIGHTS
            - Work environment preferences based on their responses
            - Leadership potential and development areas
            - Entrepreneurial indicators (if any)
            - Work-life balance considerations

            Please provide a comprehensive, actionable analysis that will give the person clear direction for their career development.

            Analyze these test responses and provide your detailed recommendations:
            """
            
            prompt += str(test_responses)
            
            print(f"Generated prompt: {prompt}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an experienced career counselor providing detailed, actionable career guidance. Be specific, practical, and encouraging while maintaining professionalism."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            if not response or not response.choices:
                raise Exception("Empty response from LLM")
            
            career_analysis = response.choices[0].message.content
            print(f"Raw LLM response: {career_analysis}")
            
            # Format the response for better readability
            formatted_analysis = career_analysis.replace('\n\n', '<br><br>')
            formatted_analysis = formatted_analysis.replace('•', '<br>•')
            
            return formatted_analysis
            
        except Exception as e:
            print(f"LLM Service Error: {str(e)}")
            raise

    def validate_responses(self, test_responses: Dict[str, List[Dict]]) -> bool:
        """
        Validates the test responses before processing
        """
        try:
            required_tests = {f'TEST{i}' for i in range(1, 5)}
            
            # Check if all tests are present
            if not all(test in test_responses for test in required_tests):
                missing_tests = required_tests - set(test_responses.keys())
                raise LLMServiceError(f"Missing test responses for: {missing_tests}")
            
            # Check if each test has responses
            for test, responses in test_responses.items():
                if not responses:
                    raise LLMServiceError(f"Empty responses for {test}")
                
                # Validate response format
                for response in responses:
                    if 'question' not in response or 'answer' not in response:
                        raise LLMServiceError(f"Invalid response format in {test}")
            
            return True
            
        except Exception as e:
            raise LLMServiceError(f"Response validation failed: {str(e)}") 