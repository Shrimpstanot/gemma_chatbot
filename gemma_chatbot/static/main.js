// --- DOM Elements ---
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const chatWindow = document.getElementById('chat-window');
const newChatBtn = document.getElementById('new-chat-btn');
const conversationList = document.getElementById('conversation-list');
const fileInput = document.getElementById('file-input');

// --- State Management ---
let activeConversationId = null;
let ws = null;
let currentGemmaMessageElement = null;

// --- TYPING EFFECT LOGIC (FINAL VERSION) ---
let tokenQueue = [];
let animationIntervalId = null;
let streamEnded = false; // NEW: Flag to track if the stream is complete

function processTokenQueue() {
    if (animationIntervalId) return; // An animation is already running

    animationIntervalId = setInterval(() => {
        if (tokenQueue.length > 0) {
            const token = tokenQueue.shift();
            if (currentGemmaMessageElement) {
                currentGemmaMessageElement.append(document.createTextNode(token));
                chatWindow.scrollTop = chatWindow.scrollHeight;
            }
        } else {
            // Queue is empty, stop the animation
            clearInterval(animationIntervalId);
            animationIntervalId = null;
            
            // --- THE FIX ---
            // Now that the animation is finished, check if the stream also ended
            if (streamEnded) {
                currentGemmaMessageElement = null;
                streamEnded = false; // Reset the flag
            }
        }
    }, 10);
}

// --- File Upload Logic ---
fileInput.addEventListener('change', async (event) => {
    if (!activeConversationId) {
        alert("Please select a conversation before uploading files.");
        return;
    }

    const files = event.target.files;
    if (!files.length) {
        return; // No files selected
    }

    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    // Get the token for the Authorization header
    const token = localStorage.getItem("access_token");
    if (!token) {
        window.location.href = "/login";
        return;
    }

    try {
        const response = await fetch(`/conversations/${activeConversationId}/files`, {
            method: 'POST',
            body: formData,
            // IMPORTANT: Do NOT set Content-Type. The browser does it for you with FormData.
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'File upload failed');
        }

        alert('Files uploaded successfully!');
        
        // Reset the file input so the user can upload the same file again if needed
        fileInput.value = ''; 

        // Refresh the chat history to show the "File uploaded" message from the server
        connectWebSocket(activeConversationId);

    } catch (error) {
        console.error('File Upload Error:', error);
        alert(`Error uploading files: ${error.message}`);
    }
});
// --- WebSocket Logic ---
function connectWebSocket(conversationId) {
    if (ws) {
        ws.close();
    }
    if (!conversationId) {
        chatWindow.innerHTML = '<p>Select a conversation or start a new one.</p>';
        return;
    }

    const socket = new WebSocket(`ws://${window.location.host}/ws/${conversationId}`);

    socket.onopen = () => {
        console.log("WebSocket connection established.");
        // First, get the token from localStorage
        const token = localStorage.getItem("access_token");
        if (!token) {
            console.error("No access token found. Please log in.");
            socket.close();
            // Optionally, redirect to login page
            window.location.href = "/login.html";
            return;
        }
        // Send the token as the first message
        socket.send(JSON.stringify({ type: "auth", token: token }));
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    socket.onclose = () => {
        console.log("WebSocket connection closed.");
    };

    socket.onerror = (error) => {
        console.error("WebSocket Error:", error);
    };

    ws = socket;
}

function handleWebSocketMessage(data) {
    if (data.type === 'start_of_stream') {
        const p = document.createElement('p');
        const strong = document.createElement('strong');
        strong.textContent = 'Gemma: ';
        p.appendChild(strong);
        chatWindow.appendChild(p);
        currentGemmaMessageElement = p;
        tokenQueue = [];
        streamEnded = false; // Reset the flag for the new stream
        if (animationIntervalId) {
            clearInterval(animationIntervalId);
            animationIntervalId = null;
        }
    } else if (data.type === 'stream') {
        tokenQueue.push(data.token);
        processTokenQueue();
    } else if (data.type === 'end_of_stream') {
        // --- THE FIX ---
        // Don't nullify the element here. Just set the flag.
        streamEnded = true;
    } else if (data.type === 'error') {
        appendMessage("Error", data.message);
    } else if (data.type === 'history') {
        chatWindow.innerHTML = '';
        data.messages.forEach(msg => {
            appendMessage(msg.role === 'user' ? 'You' : 'Gemma', msg.content);
        });
    }
}

// --- Conversation Management & Other Functions ---

/**
 * Creates the authorization headers for API requests.
 * Redirects to login if the token is missing.
 * @returns {HeadersInit|null}
 */
function getAuthHeaders() {
    const token = localStorage.getItem("access_token");
    if (!token) {
        console.error("No access token found. Redirecting to login.");
        window.location.href = "/login.html";
        return null;
    }
    return {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
    };
}

async function fetchAndRenderConversations() {
    const headers = getAuthHeaders();
    if (!headers) return; // Stop if no token

    try {
        // Use the headers in the fetch request
        const response = await fetch('/conversations', { headers });

        if (!response.ok) {
            // If unauthorized, redirect to login
            if (response.status === 401) {
                window.location.href = "/login.html";
            }
            throw new Error('Failed to fetch conversations');
        }

        const data = await response.json();
        conversationList.innerHTML = '';
        data.forEach(conv => {
            const li = document.createElement('li');
            li.textContent = conv.title;
            li.dataset.id = conv.id;
            if (conv.id === activeConversationId) li.classList.add('active');
            conversationList.appendChild(li);
        });

        // If no conversation is active, and there are conversations, activate the first one.
        if (!activeConversationId && data.length > 0) {
            setActiveConversation(data[0].id);
        } else if (data.length === 0) {
            // If the user has no conversations at all, create a new one.
            await createNewConversation();
        }
    } catch (error) {
        console.error("Error fetching conversations:", error);
    }
}

async function createNewConversation() {
    const headers = getAuthHeaders();
    if (!headers) return; // Stop if no token

    try {
        const response = await fetch('/conversations', {
            method: 'POST',
            headers: headers, // Use the authenticated headers
            body: JSON.stringify({ title: "New Chat" })
        });

        if (!response.ok) {
            if (response.status === 401) window.location.href = "/login.html";
            throw new Error('Failed to create new conversation');
        }

        const newConv = await response.json();
        // After creating, refresh the whole list to ensure UI is consistent
        // and activate the new conversation.
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

async function initializeApp() {
    await fetchAndRenderConversations();
}

// --- Event Listeners ---
newChatBtn.addEventListener('click', createNewConversation);

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
    const message = messageInput.value.trim();
    if (message && ws && ws.readyState === WebSocket.OPEN) {
        appendMessage("You", message);
        ws.send(JSON.stringify({ message: message }));
        messageInput.value = '';
    }
});

function appendMessage(sender, text) {
    const messageElement = document.createElement('p');
    const strong = document.createElement('strong');
    strong.textContent = `${sender}: `;
    messageElement.appendChild(strong);
    messageElement.append(document.createTextNode(text));
    chatWindow.appendChild(messageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// --- App Initialization ---
document.addEventListener('DOMContentLoaded', initializeApp);
