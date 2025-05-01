import os
import openai
import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import JsonResponse
from PyPDF2 import PdfReader  # For PDF files
from gtts import gTTS
import logging
# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def interview_page(request):
    """Render the interview page."""
    return render(request, 'interview/interview.html')  # Ensure this template exists

def extract_text_from_resume(resume):
    """Extract text from the uploaded resume file."""
    if resume.name.endswith('.pdf'):
        reader = PdfReader(resume)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ''  # Handle None case
        return text
    else:
        return None  # Unsupported file type

def analyze_resume_and_generate_questions(interview_type, resume_text):
    prompt = f"""
    Analyze the following resume text and determine the type of interview based on the content. 
    Generate relevant interview questions without mentioning numbers before questions specifically for a {interview_type} interview, including some external questions related to the interview type and a few problem-solving questions. 
    Ensure that all questions are presented in a single list without any separation. and replace the numbers at starting of the question by empty space
   only 5 questions
    Resume Text:
    {resume_text}

    Please provide single list of questions.
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    # Assuming the response is a string of questions separated by new lines
    questions_text = response['choices'][0]['message']['content']
    questions_list = questions_text.split('\n')  # Split into a list
    # questions_extendedlist = questions_list[(questions_list.index("problem solving questions")):]
    # final_question_list = questions_list[4:questions_list[questions_list.index("problem solving questions")-1]] + questions_extendedlist
    return questions_list[1:]


def process_user_response(request):
    """Process the user's response containing the interview type and resume."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method. Only POST is allowed.'})

    interview_type = request.POST.get('interviewType')
    resume = request.FILES.get('resume')

    # Validate input
    if not interview_type:
        return JsonResponse({'status': 'error', 'message': 'Interview type is required.'})
    if not resume:
        return JsonResponse({'status': 'error', 'message': 'Resume file is required.'})

    # Extract text from the resume
    resume_text = extract_text_from_resume(resume)
    if resume_text is None:
        return JsonResponse({'status': 'error', 'message': 'Unsupported file type. Please upload a PDF.'})

    try:
        # Call OpenAI to generate questions
        questions = analyze_resume_and_generate_questions(interview_type, resume_text)

        # Check if questions were generated
        if not questions:
            return JsonResponse({'status': 'error', 'message': 'No questions generated. Please check the resume content.'})

        # Generate voice output for the questions
        questions_text = "\n".join(questions)  # Join questions into a single string
        audio_file_path = './questions.mp3'  # Path to save the audio file
        
        try:
            tts = gTTS(text=questions_text, lang='en')
            tts.save(audio_file_path)
        except Exception as tts_error:
            logging.error(f"Error generating audio file: {str(tts_error)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'An error occurred while generating audio. Please try again later.'})

        # Return the generated questions and the audio file path
        return JsonResponse({
            'status': 'success',
            'questions': questions,
            'audio_file': audio_file_path  # Return the path to the audio file
        })

    except Exception as e:
        # Log the exception for debugging purposes
        logging.error(f"Error processing user response: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An error occurred while processing your request. Please try again later.'})


@csrf_exempt
def generate_feedback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_responses = data.get('responses', [])

            # Generate feedback using OpenAI
            prompt = f"""Provide genuine feedback on the following interview responses:\n{user_responses}\n describe the user's abilities based on {user_responses} for 
            example 
            communication skills : out of 100%
             problem solving skills : out of 100%
            technical skills : out of 100% 
            and rate these skills genuinely which means very srtictly consider each and every terms and then rate out of 100%
            improvement areas:
            atlast describe what needs to be improve"""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )

            feedback_text = response['choices'][0]['message']['content']
            feedback_list = feedback_text.split('\n')  # Split feedback into a list

            return JsonResponse({
                'status': 'success',
                'feedback': feedback_list
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})