"""Tag Autocomplete Neo Plus: settings and local related-tag lookup.
Features adapted from newtextdoc1111/ComfyUI-Autocomplete-Plus (MIT).
"""
from pathlib import Path
import sqlite3
import gradio as gr
from fastapi import Query
from modules import script_callbacks, shared
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'plus_data' / 'related.sqlite3'

def settings():
    section = ('tac_plus', 'Tag Autocomplete Neo Plus')
    options = {
        'tacplus_enabled': shared.OptionInfo(True, '追加機能を有効化'),
        'tacplus_related': shared.OptionInfo(True, '関連タグを表示'),
        'tacplus_related_trigger': shared.OptionInfo('Ctrl+Click', '関連タグを開く操作（Ctrl+Shift+Spaceも利用可）', gr.Radio, {'choices':['Ctrl+Click','Click','Shortcut only']}),
        'tacplus_related_limit': shared.OptionInfo(30, '関連タグの最大表示件数', gr.Slider, {'minimum':5,'maximum':100,'step':5}),
        'tacplus_related_sort': shared.OptionInfo('Jaccard', '関連タグの並び順', gr.Radio, {'choices':['Jaccard','Co-occurrence']}),
        'tacplus_duplicates': shared.OptionInfo(True, '入力済みの補完候補をグレー表示'),
        'tacplus_duplicate_select': shared.OptionInfo(True, '入力済みの候補を選ぶと重複挿入せず既存タグを選択'),
        'tacplus_kana': shared.OptionInfo(True, '日本語検索でひらがな・カタカナ・全半角を同一視'),
        'tacplus_format': shared.OptionInfo(True, 'プロンプト整形を有効化（Alt+Shift+F）'),
        'tacplus_format_mode': shared.OptionInfo('Manual', '整形の実行タイミング', gr.Radio, {'choices':['Manual','On blur']}),
        'tacplus_format_trailing': shared.OptionInfo(False, '整形後の行末にカンマを付ける'),
        'tacplus_format_trim': shared.OptionInfo(True, '整形時に先頭・末尾の空白を削除'),
        'tacplus_input_delay': shared.OptionInfo(120, 'プロンプト内部同期の待ち時間（ms）', gr.Slider, {'minimum':60,'maximum':500,'step':10}),
    }
    for key, info in options.items():
        info.section=section
        shared.opts.add_option(key,info)

def related_rows(tag, limit=30, sort='Jaccard'):
    if not DB.is_file():
        return {'items':[], 'error':'関連タグ索引がありません'}
    tag=tag.strip().replace(' ','_')
    with sqlite3.connect(f'{DB.as_uri()}?mode=ro',uri=True) as con:
        root=con.execute('SELECT count FROM tags WHERE tag=?',(tag,)).fetchone()
        if not root: return {'items':[], 'tag':tag}
        order='n' if sort=='Co-occurrence' else 'score'
        rows=con.execute(f'''WITH edges AS (
            SELECT b AS tag,n FROM pairs WHERE a=? UNION ALL SELECT a AS tag,n FROM pairs WHERE b=?
        ) SELECT t.tag,t.category,t.count,t.alias,e.n,
          CASE WHEN ?+t.count-e.n>0 THEN e.n/(?+t.count-e.n) ELSE 0 END AS score
          FROM edges e JOIN tags t ON t.tag=e.tag WHERE t.tag!=?
          ORDER BY {order} DESC,t.tag LIMIT ?''',(tag,tag,root[0],root[0],tag,max(5,min(100,int(limit))))).fetchall()
    return {'tag':tag,'items':[dict(zip(('tag','category','count','alias','cooccurrence','score'),r)) for r in rows]}

def api(_, app):
    @app.get('/tac-plus/related')
    def related(tag: str = Query(...,max_length=256)):
        if not shared.opts.data.get('tacplus_enabled',True) or not shared.opts.data.get('tacplus_related',True):
            return {'items':[], 'disabled':True}
        return related_rows(tag,shared.opts.data.get('tacplus_related_limit',30),shared.opts.data.get('tacplus_related_sort','Jaccard'))
script_callbacks.on_ui_settings(settings)
script_callbacks.on_app_started(api)

