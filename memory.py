import utils
import chat_api

def extract_dicts_overlap_corrected(query,lst):
    """
    使记忆窗口在short_term_memory.json中进行滑动。
    :param query:
    :param lst:
    :return:
    """
    results = []
    step = 12  # 每次取出的字典数量
    overlap = 6  # 每次取出时与上一次重叠的字典数量
    # 计算总共需要取多少次
    total_steps = (len(lst) - step) // (step - overlap) + 1
    # 记录上一次取的结束索引
    last_start_index = None
    for i in range(total_steps):
        # 如果是第一次取，则从列表末尾开始取
        if i == 0:
            start_index = len(lst) - step
        # 否则，从上一次取的开始索引减去（步长-重叠的数量）开始取
        else:
            start_index = last_start_index - (step - overlap)
        # 计算结束索引
        end_index = start_index + step
        # 从列表中取出字典
        extracted = lst[start_index:end_index]
        results.append(extracted)
        # 更新上一次取的开始索引
        last_start_index = start_index
        delect = delect_to_select(query,results[-1])
        print("delect:",delect)
        if delect:
            return results[-1]
    # 如果最后还有剩余的字典，则全部取出
    if last_start_index is not None and last_start_index > 0:
        results.append(lst[:last_start_index])
    delect = delect_to_select(query, results[-1])
    if delect:
        return results[-1]
    else:
        return results[0]

def short_term_memory_window(query:str):
    '''
    记忆窗口，能存储10条会话消息。会在short_term_memory.json进行滑动，来找寻能对本次问答有帮助的内容。
    :param :
    :return:messages:[{"role":"","content":""},...]
    '''
    messages = []
    hps = utils.get_hparams_from_file("configs/short_term_memory.json")
    short_term_memory = hps.short_term_memory
    if short_term_memory.__len__() <= 12 :
        delect = delect_to_select(query,short_term_memory)
        #print(delect)
        messages.append({"role":"user","content":str(short_term_memory)+"\n请你结合前面的信息来回答这个问题:"+query})
        #print(chat_api.create_chat_completion("zhipu_api", messages))
    else:
        #print(short_term_memory.__len__())
        short_term_memory = extract_dicts_overlap_corrected(query,short_term_memory)
        #print(short_term_memory)
        messages.append({"role": "user", "content": str(short_term_memory) + "\n请你结合前面的信息来回答这个问题:" + query})
        #print(chat_api.create_chat_completion("zhipu_api", messages))
    return messages

def delect_to_select(query:str,messages:list):
    '''
    判断这段记忆对本次问答是否有帮助
    :param query:
    :return:
    '''
    template_prompt = '''
    1.你回复的格式必须严格按照我的下面要求，你只能回复True或者False，禁止回答多余内容。
    2.我会提供一个问题和一些聊天记录，聊天记录是user和assistant的一些问答对话，你需要判断我提供的这段对话记录是否存在能回答我本次提供的这个问题的信息，你只能回答True或者False。
    3.其中user代表我，assistant代表你。
    '''
    Messages = []
    Messages.append({"role":"system","content":template_prompt})
    Messages.append({"role":"assistant","content":"好的，我只会回复True或者False"})
    Messages.append({"role":"user","content":"我本次提供的问题是:"+query+"。\n而我提供的聊天记录为:"+str(messages)})
    #print("Messages:",Messages)
    return bool(chat_api.create_chat_completion("zhipu_api",Messages))

if __name__ == '__main__':

    short_term_memory_window("我喜欢什么小动物？")