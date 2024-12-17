from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import os
import pandas as pd
from dotenv import load_dotenv
import markdown2
import logging
import traceback
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Flask app with static files from root directory
app = Flask(__name__, static_url_path='', static_folder='.')

try:
    # Configure Gemini AI
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    genai.configure(api_key=api_key)
    
    # Delete any existing Firebase app instance
    try:
        firebase_admin.delete_app(firebase_admin.get_app())
    except:
        pass

    # Initialize Firebase with credentials
    cred = credentials.Certificate('chatbott-5a05f-firebase-adminsdk-68y6e-2ee1ca6053.json')
    firebase_admin.initialize_app(cred, {
        'projectId': 'chatbott-5a05f'
    })
    db = firestore.client()
    
    # Load the scholarship dataset
    DATASET_PATH = 'scholarship_dataset_combined.csv'
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset file not found: {DATASET_PATH}")
    
    logger.info(f"Loading dataset from {DATASET_PATH}")
    scholarships_df = pd.read_csv(DATASET_PATH)
    logger.info(f"Dataset loaded successfully with {len(scholarships_df)} rows")
    
    # Create dataset summary for context
    total_scholarships = len(scholarships_df)
    education_levels = scholarships_df['Education Qualification'].unique().tolist()
    communities = scholarships_df['Community'].unique().tolist()
    religions = scholarships_df['Religion'].unique().tolist()
    
    DATASET_SUMMARY = f"""
    Scholarship Database Summary:
    - Total Scholarships: {total_scholarships}
    - Education Levels: {', '.join(education_levels)}
    - Communities: {', '.join(communities)}
    - Religions: {', '.join(religions)}
    """
    logger.info(f"Dataset summary created: {DATASET_SUMMARY}")
    
except Exception as e:
    logger.error("Error during initialization:")
    logger.error(traceback.format_exc())
    raise

def format_message(content, role):
    try:
        formatted_content = markdown2.markdown(content) if role == 'assistant' else content
        return formatted_content
    except Exception as e:
        logger.error(f"Error formatting message: {str(e)}")
        return content

def get_scholarship_stats():
    """Get statistical information about scholarships"""
    stats = {
        'total': len(scholarships_df),
        'by_education': scholarships_df['Education Qualification'].value_counts().to_dict(),
        'by_community': scholarships_df['Community'].value_counts().to_dict(),
        'by_religion': scholarships_df['Religion'].value_counts().to_dict(),
        'by_gender': scholarships_df['Gender'].value_counts().to_dict()
    }
    return stats

def find_relevant_scholarships(student_info, query=None):
    """Find scholarships matching student criteria and query"""
    try:
        logger.info(f"Finding scholarships for student info: {student_info}")
        matches = []
        
        # Base filters
        filters = []
        
        # Education level filter
        education_level = student_info.get('educationLevel', '').lower()
        if education_level:
            if 'high school' in education_level or '12' in education_level:
                filters.append(scholarships_df['Education Qualification'].str.contains('12|high school|secondary', case=False, na=False))
            elif 'undergraduate' in education_level or 'bachelor' in education_level:
                filters.append(scholarships_df['Education Qualification'].str.contains('undergraduate|bachelor|UG', case=False, na=False))
            elif 'postgraduate' in education_level or 'master' in education_level:
                filters.append(scholarships_df['Education Qualification'].str.contains('postgraduate|master|PG', case=False, na=False))

        # Community filter
        category = student_info.get('category', '').upper()
        if category:
            filters.append(scholarships_df['Community'].str.contains(category, case=False, na=False))

        # Income filter
        try:
            income = float(student_info.get('income', 0))
            scholarships_df['Income_Numeric'] = scholarships_df['Income'].apply(lambda x: float('inf') if pd.isna(x) else float(x.replace('Upto ', '').replace('L', '')) * 100000 if 'Upto' in str(x) else float('inf'))
            filters.append(scholarships_df['Income_Numeric'] >= income)
        except (ValueError, TypeError):
            logger.warning("Invalid income value, skipping income filter")

        # Percentage filter
        try:
            percentage = float(student_info.get('percentage', 0))
            scholarships_df['Min_Percentage'] = scholarships_df['Annual-Percentage'].apply(lambda x: float(str(x).split('-')[0]) if pd.notna(x) and '-' in str(x) else 0)
            filters.append(scholarships_df['Min_Percentage'] <= percentage)
        except (ValueError, TypeError):
            logger.warning("Invalid percentage value, skipping percentage filter")

        # Apply all filters
        if filters:
            filtered_df = scholarships_df[pd.concat(filters, axis=1).all(axis=1)]
        else:
            filtered_df = scholarships_df

        # If there's a specific query, try to match it
        if query:
            query = query.lower()
            query_matches = []
            
            # Search in scholarship names
            name_matches = filtered_df[filtered_df['Name'].str.lower().str.contains(query, na=False)]
            query_matches.extend(name_matches.to_dict('records'))
            
            # Search in education qualification
            edu_matches = filtered_df[filtered_df['Education Qualification'].str.lower().str.contains(query, na=False)]
            query_matches.extend(edu_matches.to_dict('records'))
            
            # Search in community
            community_matches = filtered_df[filtered_df['Community'].str.lower().str.contains(query, na=False)]
            query_matches.extend(community_matches.to_dict('records'))
            
            # Remove duplicates
            seen = set()
            matches = []
            for item in query_matches:
                item_hash = item['Name']
                if item_hash not in seen:
                    seen.add(item_hash)
                    matches.append(item)
        else:
            matches = filtered_df.to_dict('records')

        # Sort matches by relevance (you can customize this)
        matches = matches[:10]  # Limit to top 10 matches
        
        logger.info(f"Found {len(matches)} matching scholarships")
        return matches
        
    except Exception as e:
        logger.error(f"Error finding scholarships: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def is_relevant_question(question):
    # Keywords related to education, scholarships, and student information
    relevant_keywords = [
        'scholarship', 'education', 'study', 'college', 'university', 'school',
        'degree', 'course', 'academic', 'student', 'financial aid', 'grant',
        'admission', 'exam', 'qualification', 'eligibility', 'application',
        'deadline', 'requirement', 'criteria', 'fee', 'stipend', 'funding',
        'merit', 'income', 'category', 'reservation', 'document', 'certificate',
        'grade', 'percentage', 'marks', 'score', 'rank', 'test', 'entrance'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in relevant_keywords)

def get_error_message():
    return ("I can only assist with questions related to education, scholarships, "
            "and student opportunities. Please ask questions within this scope. "
            "For example, you can ask about:\n"
            "- Scholarship eligibility\n"
            "- Application processes\n"
            "- Educational requirements\n"
            "- Financial aid opportunities\n"
            "- Academic programs\n"
            "- Admission criteria")

def format_scholarship_response(student_info, response_text):
    """Format the response in a structured way with enhanced formatting"""
    
    template = f"""## 🎓 Scholarship Recommendations

### 👤 Your Profile Summary
| Category | Details |
|----------|---------|
| 📚 Education | **{student_info.get('educationLevel')}** |
| 💰 Income | **₹{student_info.get('income'):,}** per annum |
| 🏷️ Category | **{student_info.get('category')}** |
| 📍 State | **{student_info.get('state')}** |
| 📊 Academic Score | **{student_info.get('percentage')}%** |

### 📋 Available Scholarships
{response_text}

### 📝 Required Documents
- Valid ID Proof (Aadhar Card)
- Income Certificate
- Category Certificate (if applicable)
- Previous Year Marksheets
- Passport Size Photographs
- Bank Account Details
- Domicile Certificate

### ⚠️ Important Guidelines
1. **Verify Eligibility**: Double-check all criteria before applying
2. **Document Preparation**: Keep all documents scanned and ready
3. **Deadlines**: Submit applications well before due dates
4. **Information Accuracy**: Ensure all details are correctly filled
5. **Follow Up**: Track your application status regularly

### 💡 Pro Tips
- ✅ Apply to multiple scholarships to increase chances
- ✅ Set calendar reminders for deadlines
- ✅ Keep copies of all submitted documents
- ✅ Follow up on your applications regularly

### ❓ Need More Information?
You can ask about:
- 📌 Specific eligibility details
- 📌 Application procedures
- 📌 Document requirements
- 📌 Selection process
- 📌 Disbursement details

*Note: All scholarship amounts and criteria mentioned are subject to change. Please verify from official sources.*
"""
    # Clean up any stray '#' characters that aren't part of headers
    template = template.replace('\n#\n', '\n').replace('\n# \n', '\n')
    return template

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/submit-info', methods=['POST'])
def submit_info():
    try:
        data = request.json
        logger.info(f"Received student info: {data}")
        
        # Validate required fields
        required_fields = [
            'fullName', 'age', 'educationLevel', 'course', 
            'income', 'category', 'state', 'percentage',
            'aadhar', 'email'
        ]
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                })
        
        # Add metadata
        data['timestamp'] = datetime.now().isoformat()
        data['submission_date'] = datetime.now().strftime('%Y-%m-%d')
        
        # Store in Firestore
        try:
            doc_ref = db.collection('student_info').document()
            doc_ref.set(data)
            
            logger.info(f"Successfully stored data with ID: {doc_ref.id}")
            
            return jsonify({
                'status': 'success',
                'message': 'Information submitted successfully',
                'doc_id': doc_ref.id
            })
        except Exception as e:
            logger.error(f"Firestore error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Database error: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"Error in submit_info: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        student_info = data.get('studentInfo', {})
        
        if not user_message:
            return jsonify({
                'status': 'error',
                'response': 'Please provide a message.'
            })
            
        if not is_relevant_question(user_message):
            return jsonify({
                'status': 'error',
                'response': get_error_message()
            })
            
        prompt = f"""Based on the student profile:
Education Level: {student_info.get('educationLevel')}
Course: {student_info.get('course')}
Annual Income: ₹{student_info.get('income')}
Category: {student_info.get('category')}
State: {student_info.get('state')}
Academic Score: {student_info.get('percentage')}%

Question: {user_message}

Provide a detailed response following this exact structure for each scholarship:

### 🏆 [Scholarship Name]
- **Eligibility**: 
  • Education requirement
  • Income criteria
  • Category criteria
  • Academic requirements

- **Benefits**: 
  • Exact amount or range
  • Coverage details
  • Additional perks

- **Application Process**:
  • Application portal link
  • Step-by-step procedure
  • Important dates

- **Selection Criteria**:
  • Merit basis
  • Interview details (if any)
  • Documentation requirements

Important:
1. List only the most relevant scholarships (maximum 3) that perfectly match the student's profile
2. Use bullet points and emphasize important information in bold
3. Include direct application links when available
4. Do not include any '#' characters except in markdown headers
5. Keep the formatting clean and consistent
"""

        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                return jsonify({
                    'status': 'error',
                    'response': 'I apologize, but I could not generate a helpful response. Please try rephrasing your question.'
                })
            
            if len(response.text) < 20:
                return jsonify({
                    'status': 'error',
                    'response': 'I apologize, but I could not generate a complete response. Please try asking your question again.'
                })
            
            formatted_response = format_scholarship_response(student_info, response.text)
                
            return jsonify({
                'status': 'success',
                'response': formatted_response
            })
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return jsonify({
                'status': 'error',
                'response': 'I encountered an error while processing your question. Please try again.'
            })
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'response': 'An unexpected error occurred. Please try again later.'
        })

if __name__ == '__main__':
    app.run(debug=True)
