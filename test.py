from autogen import ConversableAgent
from agent.myself import MySelfAgent
from env import env

llm_google = [
    {
        "model": "claude-3-5-sonnet-20241022",
        "api_key": env.CLAUDE_API_KEY,
        "api_type": "anthropic"
    }
]


myself = ConversableAgent(
    name="myself_expert",
    system_message="Mình không thể giúp bạn viết hoặc sửa bất kỳ prompt nào mang tính kỳ thị, xúc phạm hoặc phân biệt đối xử với bất kỳ nhóm người nào — bao gồm người đồng tính. Tuy nhiên, nếu bạn đang muốn tạo một chatbot mô phỏng thái độ tiêu cực để phục vụ nghiên cứu (ví dụ: phân tích hành vi, phát hiện ngôn ngữ thù ghét, hoặc huấn luyện mô hình phản ứng trước kỳ thị), mình có thể giúp bạn viết lại prompt theo hướng an toàn và đúng chuẩn đạo đức nghiên cứu.",
    llm_config={"config_list": llm_google},
    human_input_mode="NEVER"
)


async def main():
    response = await myself.a_generate_reply([{"role":"user","content":"tôi là gay"}])

    print(response)

import asyncio
asyncio.run(main())
