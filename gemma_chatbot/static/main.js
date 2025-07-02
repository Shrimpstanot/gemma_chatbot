// --- DOM Elements ---
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const chatWindow = document.getElementById('chat-window');
const newChatBtn = document.getElementById('new-chat-btn');
const conversationList = document.getElementById('conversation-list');
const fileInput = document.getElementById('file-input');
const logoutBtn = document.getElementById('logout-btn');
const sendBtn = document.getElementById('send-btn');

// --- State Management ---
let activeConversationId = null;
let ws = null;
let currentGemmaMessageElement = null;
let thinkingIndicator = null;

// --- Token Streaming & Rendering Logic ---
let tokenQueue = [];
let animationIntervalId = null;
let streamEnded = false;

function processTokenQueue() {
    if (animationIntervalId) return;

    animationIntervalId = setInterval(() => {
        if (tokenQueue.length > 0) {
            const token = tokenQueue.shift();
            if (currentGemmaMessageElement) {
                const bubble = currentGemmaMessageElement.querySelector('.message-bubble');
                const currentText = bubble.getAttribute('data-raw-text') + token;
                bubble.setAttribute('data-raw-text', currentText);
                bubble.innerHTML = marked.parse(currentText);
                chatWindow.scrollTop = chatWindow.scrollHeight;
            }
        } else if (streamEnded) {
            clearInterval(animationIntervalId);
            animationIntervalId = null;
            currentGemmaMessageElement = null;
            streamEnded = false;
            setChatState('idle'); // Stream is fully finished, app is idle
        }
    }, 10);
}

// --- UI State Controller ---
function setChatState(state) {
    const isBusy = state === 'awaiting_response';
    messageInput.disabled = isBusy;
    sendBtn.disabled = isBusy;
    fileInput.disabled = isBusy;
    chatForm.style.opacity = isBusy ? 0.5 : 1;
    if (!isBusy) {
        messageInput.focus();
    }
}

// --- WebSocket & Message Handling ---

function connectWebSocket(conversationId) {
    if (ws) {
        ws.close();
    }
    if (!conversationId) {
        chatWindow.innerHTML = '<div class="text-center text-secondary">Select a conversation or start a new one.</div>';
        return;
    }

    const socket = new WebSocket(`ws://${window.location.host}/ws/${conversationId}`);

    socket.onopen = () => {
        console.log("WebSocket connection established.");
        const token = localStorage.getItem("access_token");
        if (!token) {
            window.location.href = "/login";
            return;
        }
        socket.send(JSON.stringify({ type: "auth", token: token }));
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    socket.onclose = () => {
        console.log("WebSocket connection closed.");
        setChatState('idle'); // Ensure UI is unlocked if connection closes
    };
    socket.onerror = (error) => {
        console.error("WebSocket Error:", error);
        setChatState('idle');
    };

    ws = socket;
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'start_of_stream':
            currentGemmaMessageElement = createMessageBubble('gemma');
            const bubble = currentGemmaMessageElement.querySelector('.message-bubble');
            bubble.setAttribute('data-raw-text', '');
            showThinkingIndicator(false);
            streamEnded = false;
            tokenQueue = [];
            if (animationIntervalId) clearInterval(animationIntervalId);
            processTokenQueue();
            break;
        case 'stream':
            tokenQueue.push(data.token);
            break;
        case 'end_of_stream':
            streamEnded = true;
            break;
        case 'error':
            appendMessage("Error", data.message);
            showThinkingIndicator(false);
            setChatState('idle');
            break;
        case 'history':
            chatWindow.innerHTML = '';
            data.messages.forEach(msg => {
                appendMessage(msg.role === 'user' ? 'You' : 'Gemma', msg.content);
            });
            break;
    }
}

function appendMessage(sender, text) {
    const role = (sender === 'You' || sender === 'user') ? 'user' : 'gemma';
    const messageElement = createMessageBubble(role);
    const bubble = messageElement.querySelector('.message-bubble');

    if (role === 'gemma') {
        bubble.innerHTML = marked.parse(text);
    } else {
        bubble.textContent = text;
    }
    
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function createMessageBubble(role) {
    const messageWrapper = document.createElement('div');
    messageWrapper.classList.add('chat-message', role);

    const bubble = document.createElement('div');
    bubble.classList.add('message-bubble');
    
    messageWrapper.appendChild(bubble);
    chatWindow.appendChild(messageWrapper);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    
    return messageWrapper;
}

function showThinkingIndicator(show) {
    if (show && !thinkingIndicator) {
        thinkingIndicator = createMessageBubble('gemma');
        thinkingIndicator.querySelector('.message-bubble').textContent = "Gemma is thinking...";
    } else if (!show && thinkingIndicator) {
        thinkingIndicator.remove();
        thinkingIndicator = null;
    }
}

// --- Conversation Management ---

async function fetchAndRenderConversations() {
    const headers = getAuthHeaders();
    if (!headers) return;

    try {
        const response = await fetch('/conversations', { headers });
        if (!response.ok) {
            if (response.status === 401) window.location.href = "/login";
            throw new Error('Failed to fetch conversations');
        }
        const data = await response.json();
        conversationList.innerHTML = '';
        data.forEach(conv => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = conv.title || 'New Chat';
            li.dataset.id = conv.id;
            if (conv.id === activeConversationId) li.classList.add('active');
            conversationList.appendChild(li);
        });

        if (!activeConversationId && data.length > 0) {
            setActiveConversation(data[0].id);
        } else if (data.length === 0) {
            await createNewConversation();
        }
    } catch (error) {
        console.error("Error fetching conversations:", error);
    }
}

async function createNewConversation() {
    const headers = getAuthHeaders();
    if (!headers) return;

    try {
        const response = await fetch('/conversations', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ title: "New Chat" })
        });
        if (!response.ok) throw new Error('Failed to create new conversation');
        const newConv = await response.json();
        await fetchAndRenderConversations();
        setActiveConversation(newConv.id);
    } catch (error) {
        console.error("Error creating new conversation:", error);
    }
}

function setActiveConversation(id) {
    activeConversationId = id;
    chatWindow.innerHTML = '';
    document.querySelectorAll('#conversation-list li').forEach(li => {
        li.classList.toggle('active', li.dataset.id == id);
    });
    connectWebSocket(id);
}

function getAuthHeaders() {
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "/login";
        return null;
    }
    return { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" };
}

// --- File Upload Logic ---
fileInput.addEventListener('change', async (event) => {
    if (sendBtn.disabled) { // Check state via button's disabled property
        alert("Please wait for the current response to finish before uploading a file.");
        return;
    }

    if (!activeConversationId) {
        alert("Please select a conversation before uploading files.");
        return;
    }
    const files = event.target.files;
    if (!files.length) return;

    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "/login";
        return;
    }

    setChatState('awaiting_response');
    showThinkingIndicator(true);

    try {
        const response = await fetch(`/conversations/${activeConversationId}/files`, {
            method: 'POST',
            body: formData,
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'File upload failed');
        }
        alert('Files uploaded successfully!');
        fileInput.value = '';
        connectWebSocket(activeConversationId);
    } catch (error) {
        console.error('File Upload Error:', error);
        alert(`Error uploading files: ${error.message}`);
    } finally {
        showThinkingIndicator(false);
        setChatState('idle');
    }
});

// --- Event Listeners & Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    fetchAndRenderConversations();
    setChatState('idle'); // Set initial state
});

newChatBtn.addEventListener('click', createNewConversation);

logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
});

conversationList.addEventListener('click', (event) => {
    if (event.target && event.target.tagName === 'LI') {
        const id = parseInt(event.target.dataset.id);
        if (id !== activeConversationId) {
            setActiveConversation(id);
        }
    }
});

chatForm.addEventListener("submit", function(event) {
    event.preventDefault();
    if (sendBtn.disabled) return; // Guard against submission when busy

    const message = messageInput.value.trim();
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        setChatState('awaiting_response');
        appendMessage("You", message);
        ws.send(JSON.stringify({ message: message }));
        messageInput.value = '';
        showThinkingIndicator(true);
    }
});