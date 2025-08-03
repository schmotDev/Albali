import panel as pn
from chatlogic import chatbot_callback  # your logic in a separate file is cleanest




pn.extension()

chat_ui = pn.chat.ChatInterface(
    callback=chatbot_callback,
    callback_user="Assistant",
)

chat_ui.send(
    "Buenos dias. Soy tu asistante, ¿como puedo ayudarte?",
    user="Assistant",
    respond=False
)
pn.serve(chat_ui, title="Albali Chatbot", port=5006, show=True)


