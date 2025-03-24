document.addEventListener('DOMContentLoaded', function() {
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
  
    function addMessage(role, text) {
      const messageDiv = document.createElement('div');
      messageDiv.textContent = (role ? role + ": " : "") + text;
      chatWindow.appendChild(messageDiv);
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }
  
    sendBtn.addEventListener('click', function() {
      const message = userInput.value.trim();
      if(!message) return;
      addMessage("You", message);
      userInput.value = "";
  
      // Send the message to the backend
      fetch('/chat/api/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ "message": message })
      })
      .then(response => response.json())
      .then(data => {
        // data.response might contain the entire LLaMA answer
        // if not streaming
        if(data && data.response) {
          addMessage("Bot", data.response);
        }
      })
      .catch(err => console.error(err));
    });
  
    // A quick helper to get CSRF token from cookies
    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for(let i=0; i<cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length+1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length+1));
            break;
          }
        }
      }
      return cookieValue;
    }
  });
  