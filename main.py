from agent.react_agent import RecipeReActAgent

def run_terminal():
    agent = RecipeReActAgent()
    print("===== 智能做饭助手（终端版）=====")
    print("输入quit退出程序\n")
    while True:
        user_input = input("你：")
        if user_input.strip().lower() == "quit":
            print("助手：再见！")
            break
        reply = agent.react_thought_action(user_input)
        print(f"助手：\n{reply}\n")

if __name__ == "__main__":
    run_terminal()
