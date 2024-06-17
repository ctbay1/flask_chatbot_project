const chatForm          = document.getElementById('chat_form');
const messagesContainer = document.getElementById('messages_container');
const messageInput      = document.getElementById('message');
const chatbot_container = document.getElementById('chatbot_container')

const categories_button  = document.getElementById('categories_icon');
const categories_section = document.getElementById('categories_section'); 

chatForm.addEventListener('submit', (event) => {
    event.preventDefault(); // Prevent the default form submission behavior

    const userMessage = messageInput.value;
    appendMessage(userMessage, "message_bubble_send");

    fetch('/', {
        method: 'POST',
        body: new FormData(chatForm),
    })
    .then(response => response.json())
    .then(data => {
        const botResponse = data.response;  // <-- Access the 'response' key in the JSON
        appendMessage(botResponse, "message_bubble_receive");
    });
    messageInput.value = '';
});

function appendMessage(message, messageClass) {
    const messageElement     = document.createElement('li');
    messageElement.innerHTML = message;
    messageElement.className = messageClass
    messagesContainer.querySelector('ul').appendChild(messageElement);
    chatbot_container.scrollTop = chatbot_container.scrollHeight; // Scroll to the bottom
}

categories_button.addEventListener('click', display_categories_section)

function display_categories_section(){
    if (categories_section.hidden == true){
        categories_section.hidden = false
    }else{
        categories_section.hidden = true
    }
}