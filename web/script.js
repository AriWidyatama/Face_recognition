const API_BASE = 'http://localhost:8888';

let addStream = null;
let recStream = null;
let recognitionInterval = null;
let livenessFrames = [];
let sessionToken = null;
let isProcessing = false;

// DOM Elements
const elements = {
    addVideo: () => document.getElementById('add-video'),
    username: () => document.getElementById('username'),
    startAddCamera: () => document.getElementById('start-add-camera'),
    captureAdd: () => document.getElementById('capture-add'),
    stopAddCamera: () => document.getElementById('stop-add-camera'),
    addMessage: () => document.getElementById('add-message'),
    
    recVideo: () => document.getElementById('rec-video'),
    startRecCamera: () => document.getElementById('start-rec-camera'),
    stopRecCamera: () => document.getElementById('stop-rec-camera'),
    recMessage: () => document.getElementById('rec-message'),
    progressContainer: () => document.getElementById('progress-container'),
    progressFill: () => document.getElementById('progress-fill'),
    blinkInstruction: () => document.getElementById('blink-instruction')
};

// Utility Functions
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');

    stopAllStreams();
}

function stopAllStreams() {
    if (addStream) {
        addStream.getTracks().forEach(track => track.stop());
        addStream = null;
    }
    if (recStream) {
        recStream.getTracks().forEach(track => track.stop());
        recStream = null;
    }
    
    if (recognitionInterval) {
        clearInterval(recognitionInterval);
        recognitionInterval = null;
    }
    
    resetUIElements();
    
    isProcessing = false;
    livenessFrames = [];
    sessionToken = null;
}

function resetUIElements() {
    elements.startAddCamera().classList.remove('hidden');
    elements.captureAdd().classList.add('hidden');
    elements.stopAddCamera().classList.add('hidden');
    
    elements.startRecCamera().classList.remove('hidden');
    elements.stopRecCamera().classList.add('hidden');
    elements.progressContainer().classList.add('hidden');
    elements.blinkInstruction().classList.add('hidden');
}

function showMessage(elementId, message, type = 'info') {
    const messageEl = document.getElementById(elementId);
    const statusClass = getStatusClass(type);
    
    messageEl.innerHTML = `
        <div class="alert alert-${type}">
            <span class="status-indicator ${statusClass}"></span>
            ${message}
        </div>`;
}

function getStatusClass(type) {
    const statusMap = {
        'success': 'status-success',
        'error': 'status-error', 
        'processing': 'status-processing',
        'info': 'status-waiting'
    };
    return statusMap[type] || 'status-waiting';
}

function captureFrame(video) {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    return new Promise((resolve) => {
        canvas.toBlob(resolve, 'image/jpeg', 0.8);
    });
}

// Add User Functions
async function startAddCamera() {
    try {
        addStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        elements.addVideo().srcObject = addStream;
        
        elements.startAddCamera().classList.add('hidden');
        elements.captureAdd().classList.remove('hidden');
        elements.stopAddCamera().classList.remove('hidden');
        
        showMessage('add-message', 'Camera started. Position your face and click capture.', 'info');
    } catch (error) {
        showMessage('add-message', 'Failed to access camera: ' + error.message, 'error');
    }
}

async function captureAndAddUser() {
    const username = elements.username().value.trim();
    
    if (!username) {
        showMessage('add-message', 'Please enter your name first.', 'error');
        return;
    }

    if (!addStream) {
        showMessage('add-message', 'Camera not started.', 'error');
        return;
    }

    showMessage('add-message', 'Capturing and processing...', 'processing');

    try {
        const video = elements.addVideo();
        const imageBlob = await captureFrame(video);
        
        const formData = new FormData();
        formData.append('name', username);
        formData.append('file', imageBlob, 'capture.jpg');

        const response = await fetch(`${API_BASE}/user/add`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (result.status === 'success') {
            showMessage('add-message', result.msg, 'success');
            elements.username().value = ''; // Clear input
        } else {
            showMessage('add-message', result.msg, 'error');
        }
    } catch (error) {
        showMessage('add-message', 'Error adding user: ' + error.message, 'error');
    }
}

function stopAddCamera() {
    if (addStream) {
        addStream.getTracks().forEach(track => track.stop());
        addStream = null;
    }
    
    elements.startAddCamera().classList.remove('hidden');
    elements.captureAdd().classList.add('hidden');
    elements.stopAddCamera().classList.add('hidden');
    
    showMessage('add-message', 'Camera stopped.', 'info');
}

// Recognition Functions
async function startRecognitionCamera() {
    try {
        recStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        elements.recVideo().srcObject = recStream;
        
        elements.startRecCamera().classList.add('hidden');
        elements.stopRecCamera().classList.remove('hidden');
        
        showMessage('rec-message', 'Starting automatic recognition...', 'processing');
        
        recognitionInterval = setInterval(performRecognition, 2000);
        
    } catch (error) {
        showMessage('rec-message', 'Failed to access camera: ' + error.message, 'error');
    }
}

async function performRecognition() {
    if (isProcessing || !recStream) return;
    
    isProcessing = true;
    
    try {
        const video = elements.recVideo();
        const imageBlob = await captureFrame(video);
        
        const formData = new FormData();
        formData.append('file', imageBlob, 'recognition.jpg');

        showMessage('rec-message', 'Processing recognition...', 'processing');

        const response = await fetch(`${API_BASE}/recognition`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (result.status === 'success') {
            sessionToken = result.session_token;
            user_id = result.user_id;
            showMessage('rec-message', `Recognition successful! User ID: ${result.user_id}. Starting liveness check...`, 'success');
            
            clearInterval(recognitionInterval);
            recognitionInterval = null;
            
            startLivenessCheck();
        } else {
            showMessage('rec-message', result.msg, 'error');
        }
    } catch (error) {
        showMessage('rec-message', 'Recognition error: ' + error.message, 'error');
    }
    
    isProcessing = false;
}

function startLivenessCheck() {
    livenessFrames = [];
    elements.blinkInstruction().classList.remove('hidden');
    elements.progressContainer().classList.remove('hidden');
    
    showMessage(
        'rec-message',
        'Please blink naturally for 3 seconds...',
        'processing'
    );
    
    let frameCount = 0;
    const fps = 10;
    const duration = 3;
    const maxFrames = fps * duration;
    
    const captureInterval = setInterval(async () => {
        if (frameCount >= maxFrames) {
            clearInterval(captureInterval);
            await performLivenessCheck();
            return;
        }
        
        try {
            const video = document.getElementById('rec-video');
            const imageBlob = await captureFrame(video);
            livenessFrames.push(imageBlob);
            frameCount++;
            
            const progress = (frameCount / maxFrames) * 100;
            elements.progressFill().style.width = progress + '%';
            
        } catch (error) {
            console.error('Error capturing liveness frame:', error);
        }
    }, 100);
}

async function performLivenessCheck() {
    try {
        showMessage('rec-message', 'Analyzing liveness...', 'processing');
        
        const formData = new FormData();
        livenessFrames.forEach((frame, index) => {
            formData.append('files', frame, `liveness_${index}.jpg`);
        });
        formData.append('session_token', sessionToken);
        formData.append('user_id', user_id);

        const response = await fetch(`${API_BASE}/liveness`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        
        if (result.status === 'success') {
            Swal.fire({
                title: 'Liveness Verified!',
                text: '✅ Authentication successful!',
                icon: 'success',
                confirmButtonText: 'OK'
            }).then(() => {
                stopRecognitionCamera()
            });
            elements.blinkInstruction().classList.add('hidden');
        } else {
            Swal.fire({
                title: 'Liveness Failed',
                text: result.msg || 'Please try again.',
                icon: 'error',
                showCancelButton: true,
                confirmButtonText: 'Ulang Cek',
                cancelButtonText: 'Stop'
            }).then((res) => {
                if (res.isConfirmed) {
                    startLivenessCheck();
                } else {
                    showMessage('rec-message', '🚫 Liveness check stopped.', 'error');
                    stopRecognitionCamera()
                }
            });
        }

        elements.blinkInstruction().classList.add('hidden');
        elements.progressContainer().classList.add('hidden');
        
    } catch (error) {
        showMessage('rec-message', 'Liveness check error: ' + error.message, 'error');
        elements.blinkInstruction().classList.add('hidden');
        elements.progressContainer().classList.add('hidden');
    }
}

function stopRecognitionCamera() {
    if (recStream) {
        recStream.getTracks().forEach(track => track.stop());
        recStream = null;
    }
    
    if (recognitionInterval) {
        clearInterval(recognitionInterval);
        recognitionInterval = null;
    }
    
    elements.startRecCamera().classList.remove('hidden');
    elements.stopRecCamera().classList.add('hidden');
    elements.progressContainer().classList.add('hidden');
    elements.blinkInstruction().classList.add('hidden');
    
    isProcessing = false;
    livenessFrames = [];
    sessionToken = null;
    
    showMessage('rec-message', 'Recognition stopped.', 'info');
}

// Event Listeners
function setupEventListeners() {
    elements.startAddCamera().addEventListener('click', startAddCamera);
    elements.captureAdd().addEventListener('click', captureAndAddUser);
    elements.stopAddCamera().addEventListener('click', stopAddCamera);
    
    elements.startRecCamera().addEventListener('click', startRecognitionCamera);
    elements.stopRecCamera().addEventListener('click', stopRecognitionCamera);
    
    elements.username().addEventListener('keypress', function(event) {
        if (event.key === 'Enter' && !elements.captureAdd().classList.contains('hidden')) {
            captureAndAddUser();
        }
    });
}

// Initialize Application
function initializeApp() {
    setupEventListeners();
    
    showMessage('add-message', 'Ready to add new users.', 'info');
    showMessage('rec-message', 'Ready for face recognition.', 'info');

    window.addEventListener('beforeunload', stopAllStreams);
}

// Make switchTab
window.switchTab = switchTab;

// Initialize DOM
document.addEventListener('DOMContentLoaded', initializeApp);