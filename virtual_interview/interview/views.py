import os
from openai import OpenAI
import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse
from PyPDF2 import PdfReader
import logging
from django.views.decorators.csrf import ensure_csrf_cookie

# Initialize OpenAI client with API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@ensure_csrf_cookie
def interview_page(request):
    """Render the interview page."""
    return render(request, 'interview/interview.html')

def extract_text_from_resume(resume):
    """Extract text from the uploaded resume file."""
    try:
        if resume.name.endswith('.pdf'):
            reader = PdfReader(resume)
            text = ''
            for page in reader.pages:
                text += page.extract_text() or ''
            return text
        else:
            return None
    except Exception as e:
        logging.error(f"Error extracting text from resume: {str(e)}")
        return None

def analyze_resume_and_generate_questions(interview_type, resume_text, skills, interests):
    """Generate interview questions based on resume, skills, and interests."""
    try:
        prompt = f"""
        Analyze the following candidate information and generate exactly 5 relevant interview questions for a {interview_type} interview.
        
        Resume Content:
        {resume_text[:3000]}  # Limit resume text to avoid token limits
        
        Skills: {skills}
        Interests: {interests}
        
        Generate exactly 5 questions that are:
        1. Relevant to the interview type: {interview_type}
        2. Based on the resume content
        3. Appropriate for the skills and interests mentioned
        
        Format: Return only the questions, one per line, without any numbering or bullet points.
        """
        
        # Updated OpenAI API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )

        questions_text = response.choices[0].message.content
        # Split by new lines and clean up
        questions_list = [q.strip() for q in questions_text.split('\n') if q.strip()]
        
        # Ensure we have exactly 5 questions
        if len(questions_list) > 5:
            questions_list = questions_list[:5]
        elif len(questions_list) < 5:
            # If we got fewer than 5, add some generic ones
            default_questions = [
                "Tell me about yourself and your background.",
                "What are your greatest strengths?",
                "How do you handle challenges in the workplace?",
                "Where do you see yourself in 5 years?",
                "Why are you interested in this position?"
            ]
            questions_list.extend(default_questions[:5-len(questions_list)])
        
        return questions_list
        
    except Exception as e:
        logging.error(f"Error generating questions: {str(e)}")
        # Return default questions if OpenAI fails
        return [
            "Tell me about yourself and your background.",
            "What are your greatest strengths?",
            "How do you handle challenges in the workplace?",
            "Where do you see yourself in 5 years?",
            "Why are you interested in this position?"
        ]

@csrf_exempt
def process_user_response(request):
    """Process the user's response containing the interview type and resume."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method. Only POST is allowed.'})

    try:
        interview_type = request.POST.get('interviewType')
        resume = request.FILES.get('resume')
        name = request.POST.get('name')
        email = request.POST.get('email')
        skills = request.POST.get('skills', '')
        interests = request.POST.get('interests', '')

        # Validate input
        if not interview_type:
            return JsonResponse({'status': 'error', 'message': 'Interview type is required.'})
        if not resume:
            return JsonResponse({'status': 'error', 'message': 'Resume file is required.'})

        # Extract text from the resume
        resume_text = extract_text_from_resume(resume)
        if resume_text is None:
            return JsonResponse({'status': 'error', 'message': 'Unsupported file type or error reading PDF.'})

        # Generate questions
        questions = analyze_resume_and_generate_questions(interview_type, resume_text, skills, interests)

        return JsonResponse({
            'status': 'success',
            'questions': questions,
            'message': f'Generated {len(questions)} questions for {interview_type} interview'
        })

    except Exception as e:
        logging.error(f"Error in process_user_response: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'})

@csrf_exempt
def generate_feedback(request):
    """Generate feedback based on user responses."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_responses = data.get('responses', {})
            
            # Create a formatted string of responses for the prompt
            responses_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in user_responses.items()])
            
            prompt = f"""
            Based on the following interview responses, provide constructive feedback:
            
            {responses_text}
            
            Please provide:
            1. Overall assessment
            2. Strengths
            3. Areas for improvement
            4. Specific suggestions
            
            Format your response as a clear, structured analysis.
            """
            
            # Updated OpenAI API call
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800
            )

            feedback_text = response.choices[0].message.content
            # Split into paragraphs for better display
            feedback_list = [p.strip() for p in feedback_text.split('\n') if p.strip()]

            return JsonResponse({
                'status': 'success',
                'feedback': feedback_list
            })

        except Exception as e:
            logging.error(f"Error generating feedback: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})