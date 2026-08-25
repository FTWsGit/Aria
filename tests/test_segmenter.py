from aria.segmenter import PlainSentenceSegmenter, segment_sentences


# ---------------------------------------------------------------------------
# segment_sentences 单元测试
# ---------------------------------------------------------------------------

def test_segment_sentences_basic():
    """句号、问号、感叹号结尾触发分段。"""
    assert segment_sentences("你好。世界。") == ["你好", "世界"]
    assert segment_sentences("真的吗？是的。") == ["真的吗", "是的"]
    assert segment_sentences("太棒了！继续。") == ["太棒了", "继续"]


def test_segment_sentences_no_split_on_semicolon():
    """分号不在分隔符列表中，不会触发分段。"""
    assert segment_sentences("第一句；第二句") == ["第一句；第二句"]


def test_segment_sentences_empty():
    """空文本返回空列表。"""
    assert segment_sentences("") == []
    assert segment_sentences("   ") == []


def test_segment_sentences_no_punctuation():
    """无标点结尾的文本整体返回。"""
    assert segment_sentences("这是一段没有标点的文本") == ["这是一段没有标点的文本"]


def test_segment_sentences_multiple():
    """多句连续输入被正确拆分。"""
    result = segment_sentences("第一句。第二句。第三句，第四句。第五句？第六句！")
    assert result == ["第一句", "第二句", "第三句", "第四句", "第五句", "第六句"]


def test_segment_sentences_pure_punctuation():
    """纯标点文本返回空列表。"""
    assert segment_sentences("。？！，、") == []
    assert segment_sentences("...") == []


def test_segment_sentences_long_sentence():
    """超过80字符的句子被强制拆分。"""
    long_text = "A" * 90
    result = segment_sentences(long_text)
    assert len(result) == 2
    assert len(result[0]) == 80
    assert len(result[1]) == 10


def test_segment_sentences_special_chars():
    """特殊字符（emoji、unicode 标点）不破坏分段逻辑。"""
    assert segment_sentences("Hello🎉。World。") == ["Hello🎉", "World"]
    assert segment_sentences("Café。naïve？") == ["Café", "naïve"]


def test_segment_sentences_chinese_punctuation():
    """中文标点（。？！，、）触发分段。"""
    assert segment_sentences("你好。再见。") == ["你好", "再见"]
    assert segment_sentences("第一，第二，第三") == ["第一", "第二", "第三"]


def test_segment_sentences_newline():
    """换行符触发分段。"""
    assert segment_sentences("第一行\n第二行") == ["第一行", "第二行"]


def test_segment_sentences_last_sentence_kept():
    """末尾无标点的句子被保留。"""
    assert segment_sentences("第一句。第二句还没说完") == ["第一句", "第二句还没说完"]


# ---------------------------------------------------------------------------
# PlainSentenceSegmenter 单元测试
# ---------------------------------------------------------------------------

def test_segmenter_process_basic_commit():
    """6句输入 → 达到阈值，提交4句，pending_draft 返回全部6句草稿。"""
    seg = PlainSentenceSegmenter()
    text = "一。二。三。四。五。六。"
    committed = seg.process_text(text)
    assert committed is not None
    assert committed == "一 二 三 四"
    # _draft_sources 在提交后不裁剪，仍包含全部6句
    assert seg.pending_draft() == "一 二 三 四 五 六"


def test_segmenter_below_threshold():
    """少于6句且少于150字符 → 不提交，返回None。"""
    seg = PlainSentenceSegmenter()
    committed = seg.process_text("一句。两句。")
    assert committed is None
    assert seg.pending_draft() == "一句 两句"


def test_segmenter_char_threshold_trigger():
    """虽然句数不足6，但总字符数≥150 → 触发提交。"""
    seg = PlainSentenceSegmenter()
    long_sentence = "X" * 150  # 会被拆成 80+70 两个句子
    committed = seg.process_text(long_sentence)
    assert committed is not None
    assert len(committed) > 0


def test_segmenter_same_text_ignored():
    """相同文本不重复处理，返回None。"""
    seg = PlainSentenceSegmenter()
    text = "一。二。三。四。五。六。"
    seg.process_text(text)
    assert seg.process_text(text) is None


def test_segmenter_pending_draft():
    """pending_draft 返回当前所有草稿（含已提交部分，因 _draft_sources 不裁剪）。"""
    seg = PlainSentenceSegmenter()
    seg.process_text("一。二。")
    assert seg.pending_draft() == "一 二"
    seg.process_text("一。二。三。四。五。六。")
    # 提交了前4句，但 _draft_sources 仍包含全部6句
    assert seg.pending_draft() == "一 二 三 四 五 六"


def test_segmenter_reset():
    """reset() 清除所有状态，后续可以重新开始。"""
    seg = PlainSentenceSegmenter()
    seg.process_text("一。二。三。四。五。六。")
    assert seg.pending_draft() != ""
    seg.reset()
    assert seg.pending_draft() == ""
    # 重置后应当重新输入
    committed = seg.process_text("一。二。")
    assert committed is None  # 2句不够阈值
    assert seg.pending_draft() == "一 二"


def test_segmenter_empty_text():
    """空文本输入不触发任何操作。"""
    seg = PlainSentenceSegmenter()
    assert seg.process_text("") is None
    assert seg.pending_draft() == ""


def test_segmenter_incremental_feed():
    """增量输入：逐步追加句子，验证累积提交。"""
    seg = PlainSentenceSegmenter()
    # 前4句不够阈值
    assert seg.process_text("一。二。三。四。") is None
    # 再追加2句，达到6句阈值
    committed = seg.process_text("一。二。三。四。五。六。")
    assert committed == "一 二 三 四"
    # _draft_sources 重新设置为 sentences[0:]，包含全部6句
    assert seg.pending_draft() == "一 二 三 四 五 六"


def test_segmenter_only_commits_new():
    """已提交的句子不会被重复提交。"""
    seg = PlainSentenceSegmenter()
    # 第一次：提交一、二、三、四
    seg.process_text("一。二。三。四。五。六。")
    # 同样的文本不变 → 不提交
    assert seg.process_text("一。二。三。四。五。六。") is None
    # 追加到10句，_committed_count=4，draft=sentences[4:]=6句 → 触发提交
    committed = seg.process_text(
        "一。二。三。四。五。六。七。八。九。十。"
    )
    assert committed == "五 六 七 八"