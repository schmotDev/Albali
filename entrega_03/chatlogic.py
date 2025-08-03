import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from vtiger import get_leads_data, get_cursos_disponibles, get_precio_curso
import json



load_dotenv()
api_key=os.environ.get("OPENROUTER_API_KEY", None)

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1"
)
model="gpt-3.5-turbo"



def retrieve_lead_data(data: str) -> str:
    lead = get_leads_data(data)
    if lead is not None:
        return json.dumps(lead)
        
    return json.dumps({"error": "there is no lead corresponding to this data"})


def retrieve_courses() -> str:
    return json.dumps(get_cursos_disponibles())

def retrieve_prices(course_name: str) -> str:
    precio = get_precio_curso(course_name)
    if precio is not None:
        return json.dumps({f"{course_name}": f"{precio}"})
    return json.dumps({f"{course_name}": "there is no course corresponding to this name"})


tools_list = [
{
    "type": "function",
    "function": {
        "name": "retrieve_lead_data",
        "description": "Get information about the lead according to some specific data he gave to the chatbot, such as name, email, or phone",
        "parameters": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "The data shared by the lead, such as his name, email or phone number",
                }
            },
            "required": ["data"],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "retrieve_courses",
        "description": "Retrieve the list of courses available",
        "parameters": {
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "retrieve_prices",
        "description": "retrive the price of a course by his name",
        "parameters": {
            "type": "object",
            "properties": {
                "course_name": {
                    "type": "string",
                    "description": "name of the course we want to retrieve the price",
                }
            },
            "required": ["course_name"],
        },
    },
}
]

functions_mapping = {
    "retrieve_lead_data": retrieve_lead_data,
    "retrieve_courses": retrieve_courses,
    "retrieve_prices": retrieve_prices,
}

chat_messages_history = []

message = {"role": "system",
           "content": """You are a helpful assistant working for a company providing courses.
                        You can answer normally to any general question.
                        You also have access to tools (functions) and should call them directly when appropriate. 
                        One tool can help you to find information about the user (lead) if he shares his name, email or phone number.
                        Another tool can help you to retrieve the list of available courses.
                        The third tool can help you to retrieve the price of a course by his name.
                        Do not ask the user for confirmation.
                        If a function is useful to fulfill the request, call it immediately.
                        Don't make assumptions about what values to plug into functions. 
                        Ask for clarification if a user request is ambiguous.
                        """,
           }



chat_messages_history.append(message)

def call_llm(model, messages, tools=False):

    params = {"model": model,
              "messages": messages,}

    if tools:
        params["tools"] = tools_list
        params["tool_choice"] = "auto"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**params)
            return response
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg:
                print(f"[Retry {attempt + 1}/{max_retries}] Rate limit exceeded. Retrying in 5 seconds...")
                time.sleep(5)

    return None




def chatbot_callback(user_input, role, chat_interface):

    message = {"role": "user",
                "content": user_input,
    }

    chat_messages_history.append(message)

    chat_response = call_llm(model, chat_messages_history, tools=True)

    if chat_response.choices[0].message.content:
        message = {"role": "assistant",
                    "content": chat_response.choices[0].message.content,}
        chat_messages_history.append(message)
        return f"{chat_response.choices[0].message.content}"

    elif chat_response.choices[0].message.tool_calls:

        message = {"role": "assistant",
                    "content": None,
                    "tool_calls": chat_response.choices[0].message.tool_calls,}
        chat_messages_history.append(message)

        for call in chat_response.choices[0].message.tool_calls:
            function_name = call.function.name
            function_args = json.loads(call.function.arguments)

            if function_name in functions_mapping:
                tool_result = functions_mapping[function_name](**function_args)
                print(f"{function_name} : {tool_result}")

                message = {"tool_call_id": call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": tool_result,
                            }
                chat_messages_history.append(message)


        chat_response = call_llm(model, chat_messages_history)
        #print(f"le chat_response du dernier call avec resultats des tools : {chat_response.choices[0].message.content}")

        message = {"role": "assistant",
                    "content": chat_response.choices[0].message.content}
        chat_messages_history.append(message)
        #print("on envoie le content du response du tool")
        return f"{chat_response.choices[0].message.content}"

    else:
        return f"No response..."



