import hashlib
import base64
from pathlib import Path
import streamlit as st
from streamlit_cropper import st_cropper
from processing import page_count, render_page, extract_ink, png_bytes, checker_preview

st.set_page_config(page_title='توقيعي | استخراج التوقيع', page_icon='✍️', layout='wide')
st.markdown('''<style>
.stApp {background: #f6f8fb;}
.block-container {max-width: 1250px; padding-top: 2.5rem;}
h1,h2,h3,p,[data-testid="stMarkdownContainer"],label {direction:rtl; text-align:right;}
h1 {color:#12352e;}
[data-testid="stVerticalBlockBorderWrapper"] {background:white; border-radius:18px;}
.app-logo {display:flex; justify-content:center; margin:0 0 24px;}
.app-logo img {width:180px; max-width:45vw; height:auto;}
</style>''', unsafe_allow_html=True)
logo = base64.b64encode((Path(__file__).parent / 'assets' / 'avatar.png').read_bytes()).decode('ascii')
st.markdown(f'<div class="app-logo"><img src="data:image/png;base64,{logo}" alt="شعار التطبيق"></div>', unsafe_allow_html=True)

with st.container(border=True):
    st.subheader('١ · ارفع الملف')
    upload = st.file_uploader('اختر ملف PDF', type=['pdf'])
    st.caption('المعالجة داخل التطبيق، دون إرسال الملف إلى خدمات ذكاء اصطناعي. عند تشغيله محليًا، تبقى الملفات على جهازك.')

if upload is None:
    st.info('ارفع الملف، ثم حدّد التوقيع بالمستطيل. ستظهر النتيجة مباشرة مع زر التنزيل.')
    st.stop()
if upload.size > 30 * 1024 * 1024:
    st.error('حجم الملف أكبر من 30 ميجابايت. ارفع ملفًا أصغر.')
    st.stop()

data = upload.getvalue()
identity = hashlib.sha256(data).hexdigest()[:16]
password = None
try:
    count = page_count(data)
except Exception:
    password = st.text_input('إذا كان الملف محميًا، أدخل كلمة المرور', type='password', key=f'pw-{identity}')
    if not password:
        st.warning('تعذّر فتح الملف. قد يكون محميًا بكلمة مرور أو غير صالح.')
        st.stop()
    try:
        count = page_count(data, password)
    except Exception:
        st.error('تعذّر فتح الملف. تحقق من كلمة المرور وسلامة ملف PDF.')
        st.stop()
if count < 1:
    st.error('الملف لا يحتوي على صفحات.')
    st.stop()

page_number = st.selectbox('الصفحة التي تحتوي على التوقيع', range(1, count + 1), index=count - 1, key=f'page-{identity}')
page_key = (identity, page_number, hashlib.sha256((password or '').encode()).hexdigest())
if st.session_state.get('render_key') != page_key:
    try:
        st.session_state['rendered_page'] = render_page(data, page_number - 1, password)
        st.session_state['render_key'] = page_key
    except Exception:
        st.error('تعذّر عرض هذه الصفحة. جرّب صفحة أخرى أو نسخة سليمة من الملف.')
        st.stop()
page = st.session_state['rendered_page']

left, right = st.columns([1.35, 1], gap='large')
with left, st.container(border=True):
    st.subheader('٢ · حدّد التوقيع')
    st.caption('اسحب المستطيل الأخضر وعدّل حجمه ليحيط بالتوقيع وحده، دون الاسم أو التاريخ.')
    cropped = st_cropper(page, realtime_update=True, box_color='#16a085', aspect_ratio=None,
                         default_coords=(int(page.width*.3), int(page.width*.7), int(page.height*.72), int(page.height*.85)),
                         key=f'crop-{identity}-{page_number}', return_type='image')
    st.caption('للتحديد الأدق: حرّك زوايا المستطيل، وتحقق من صورة المنطقة المحددة على اليمين.')

with right, st.container(border=True):
    st.subheader('٣ · عاين ونزّل')
    if cropped.width < 2 or cropped.height < 2:
        st.warning('وسّع مستطيل التحديد قليلًا.')
        st.stop()
    st.image(cropped, caption='المنطقة المحددة قبل إزالة الخلفية', width='stretch')
    cutoff = st.slider('حساسية الاحتفاظ بالحبر', 120, 254, 235,
                       help='ارفع القيمة للتوقيع الباهت. اخفضها لإزالة ظلال الورق والنقاط الرمادية.')
    color = st.radio('لون التوقيع', ['أسود', 'الاحتفاظ بلون الحبر'], horizontal=True)
    trim = st.checkbox('قصّ الهوامش الفارغة تلقائيًا', value=True)
    try:
        result = extract_ink(cropped, cutoff, color == 'أسود', trim)
    except ValueError as error:
        st.warning(str(error))
        st.stop()
    st.image(checker_preview(result), caption='المربعات للمعاينة فقط؛ الصورة المنزّلة شفافة.', width='stretch')
    st.download_button('↓ تنزيل التوقيع الشفاف', png_bytes(result),
                       file_name=f'{Path(upload.name).stem}-signature-p{page_number}.png',
                       mime='image/png', type='primary', width='stretch')
    st.caption(f'PNG شفاف · {result.width} × {result.height} بكسل')
    st.caption('الأفضل توقيع داكن على ورق فاتح. أي نص أو خط داخل التحديد سيبقى معه؛ ضيّق المستطيل لاستبعاده.')
