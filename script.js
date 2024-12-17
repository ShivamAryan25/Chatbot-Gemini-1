document.addEventListener('DOMContentLoaded', function() {
    const studentForm = document.getElementById('studentForm');
    const chatContainer = document.getElementById('chat-container');
    const userInput = document.getElementById('user-input');
    let studentData = null;

    function renderMarkdown(text) {
        // Replace markdown headers with emojis
        text = text.replace(/## (.*)/g, '<h2 class="text-2xl font-bold mt-6 mb-4 text-indigo-700">$1</h2>');
        text = text.replace(/### (.*)/g, '<h3 class="text-xl font-semibold mt-5 mb-3 text-indigo-600">$1</h3>');
        
        // Convert markdown tables
        text = text.replace(/\|.*\|/g, function(match) {
            if (match.includes('-------')) {
                return ''; // Skip separator line
            }
            const cells = match.split('|').filter(cell => cell.trim());
            const isHeader = match.includes('Category');
            
            if (isHeader) {
                return `<div class="grid grid-cols-2 gap-4 bg-indigo-50 p-3 rounded-t-lg font-semibold">
                    ${cells.map(cell => `<div class="text-indigo-700">${cell.trim()}</div>`).join('')}
                </div>`;
            } else {
                return `<div class="grid grid-cols-2 gap-4 border-b p-3">
                    ${cells.map(cell => `<div>${cell.trim()}</div>`).join('')}
                </div>`;
            }
        });
        
        // Convert bullet points with emojis
        text = text.replace(/- (.*)/g, '<li class="ml-4 mb-2 flex items-start"><span class="mr-2">•</span>$1</li>');
        
        // Convert numbered lists
        text = text.replace(/(\d+)\. (.*)/g, '<div class="ml-4 mb-2 flex items-start"><span class="mr-2 font-semibold">$1.</span>$2</div>');
        
        // Replace bold text
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-indigo-900">$1</strong>');
        
        // Convert italics
        text = text.replace(/\*(.*?)\*/g, '<em class="text-gray-600">$1</em>');
        
        // Convert URLs to links
        text = text.replace(/\[(.*?)\]\((.*?)\)/g, 
            '<a href="$2" class="text-blue-600 hover:underline hover:text-blue-800" target="_blank">$1</a>'
        );
        
        return text;
    }

    function showMessage(message, type = 'system') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type} mb-4 p-4 rounded-lg ${
            type === 'user' ? 'bg-blue-100' : 
            type === 'assistant' ? 'bg-white shadow-sm border border-gray-100' : 
            type === 'error' ? 'bg-red-50 border border-red-100' : 
            'bg-gray-50'
        }`;
        
        if (type === 'assistant') {
            messageDiv.innerHTML = renderMarkdown(message);
            // Add scholarship-specific styling
            messageDiv.classList.add('scholarship-response');
            messageDiv.classList.add('prose', 'max-w-none');
        } else {
            messageDiv.textContent = message;
        }
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function showFormSummary(formData) {
        const summaryHTML = `
            <div class="bg-white p-6 rounded-lg shadow-sm mb-6">
                <h3 class="text-lg font-semibold mb-4">Submitted Information</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <p class="text-sm font-medium text-gray-500">Full Name</p>
                        <p class="text-gray-900">${formData.fullName}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">Age</p>
                        <p class="text-gray-900">${formData.age}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">Education Level</p>
                        <p class="text-gray-900">${formData.educationLevel}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">Course</p>
                        <p class="text-gray-900">${formData.course}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">Annual Family Income</p>
                        <p class="text-gray-900">₹${formData.income}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">Category</p>
                        <p class="text-gray-900">${formData.category}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">State</p>
                        <p class="text-gray-900">${formData.state}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">Previous Year Percentage</p>
                        <p class="text-gray-900">${formData.percentage}%</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">Aadhar Number</p>
                        <p class="text-gray-900">${formData.aadhar}</p>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-500">Email Address</p>
                        <p class="text-gray-900">${formData.email}</p>
                    </div>
                </div>
            </div>
        `;
        
        const summaryDiv = document.createElement('div');
        summaryDiv.innerHTML = summaryHTML;
        chatContainer.insertBefore(summaryDiv, chatContainer.firstChild);
    }

    if (studentForm) {
        studentForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                fullName: document.getElementById('fullName').value.trim(),
                age: parseInt(document.getElementById('age').value),
                educationLevel: document.getElementById('educationLevel').value,
                course: document.getElementById('course').value.trim(),
                income: parseInt(document.getElementById('income').value),
                category: document.getElementById('category').value,
                state: document.getElementById('state').value,
                percentage: parseFloat(document.getElementById('percentage').value),
                aadhar: document.getElementById('aadhar').value.trim(),
                email: document.getElementById('email').value.trim()
            };

            // Validate form data
            for (const [key, value] of Object.entries(formData)) {
                if (!value && value !== 0) {
                    showMessage(`Please fill in the ${key.replace(/([A-Z])/g, ' $1').toLowerCase()}`, 'error');
                    return;
                }
            }

            try {
                const response = await fetch('/submit-info', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();
                
                if (result.status === 'success') {
                    studentForm.style.display = 'none';
                    studentData = formData;
                    
                    // Show form summary
                    showFormSummary(formData);
                    
                    showMessage('Information submitted successfully! You can now ask questions about scholarships and opportunities.', 'system');
                } else {
                    showMessage('Error submitting information: ' + result.message, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showMessage('Error submitting information. Please try again.', 'error');
            }
        });
    }

    // Handle sending messages
    window.sendMessage = async function() {
        if (!studentData) {
            showMessage('Please submit your information first.', 'error');
            return;
        }

        const message = userInput.value.trim();
        if (!message) return;

        showMessage(message, 'user');
        userInput.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    studentInfo: studentData
                })
            });

            const data = await response.json();
            
            if (data.status === 'success') {
                showMessage(data.response, 'assistant');
            } else {
                showMessage(data.response, 'error');
                
                // If it's an out-of-scope question, add a helpful suggestion
                if (data.response.includes("I can only assist with questions related to education")) {
                    showMessage("Try asking about scholarships, educational opportunities, or admission requirements that match your profile.", 'system');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showMessage('Error communicating with the server. Please try again.', 'error');
        }
    }

    // Handle Enter key in chat input
    if (userInput) {
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});
