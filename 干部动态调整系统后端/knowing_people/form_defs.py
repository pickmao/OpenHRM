"""知事识人各附件的栏目定义、默认值和提交校验。"""

from copy import deepcopy

from rest_framework.exceptions import ValidationError

from .models import FormType


SELF_EVAL_GRADES = ['优', '良', '中', '差']
RECOGNITION_OPTIONS = ['认可', '基本认可', '不认可', '不了解']
PERSONNEL_CATEGORIES = ['党支部书记', '党支部支委', '党支部全体民警职工']
MATRIX_GRADES = ['优', '良', '中', '差']
TALK_GRADES = ['好', '较好', '一般', '差']
ROLES = ['主导者', '协助者', '执行者']
EXPERIENCE_STRUCTURES = ['长期在机关', '相对均衡', '长期在监区']
MARITAL_STATUSES = ['已婚', '未婚', '离异', '丧偶', '其他']

SELF_DIMENSIONS = [{'key': 'political',
  'label': '政治站位高不高',
  'content': '是否坚决贯彻执行上级和监狱党委的决策部署，把监狱重点工作作为重大政治任务抓落实；是否在关键时期、重大原则问题上政治立场坚定，政治方向正确；是否具备较强的政治鉴别力和政治敏感性。'},
 {'key': 'integrity',
  'label': '道德品行优不优',
  'content': '是否廉洁自律，公正廉明；是否践行社会主义核心价值观，弘扬中华优秀传统美德；是否自觉远离低级趣味，坚决抵制歪风邪气，恪守社会公德、职业道德、家庭美德和个人品德。'},
 {'key': 'responsibility',
  'label': '责任担当硬不硬',
  'content': '是否在急难险重任务面前，不讲条件、不打折扣、义不容辞、冲锋在前；是否在困难面前，迎难而上、勇挑重担、力解难题；是否只会被人推着走，不愿主动干；是否关键时刻顶得上、靠得住。'},
 {'key': 'style',
  'label': '行为作风正不正',
  'content': '是否坚决杜绝形式主义、官僚主义；是否依靠群众、脚踏实地、稳扎稳打、善作善成；是否人前一个样，人后一个样；是否自觉保持干净的生活圈和社交圈；是否作风正派、公道老实。'},
 {'key': 'thinking',
  'label': '工作思路清不清',
  'content': '是否在贯彻上级精神上坚定不移，在落实工作要求上不折不扣；是否结合实际、与时俱进创造性地开展业务工作；是否熟练掌握所在岗位的业务知识，胜任本职岗位职责；是否能团结同事、凝聚人心；是否有拿得下、战必胜的坚定信心和决心。'},
 {'key': 'frontline',
  'label': '践行一线实不实',
  'content': '是否做到靠前指挥，深入一线去发现和解决问题；是否践行“一线工作法”，切实把重心力量下沉到基层一线；是否服务好基层一线，千方百计解决一线工作难题，优质资源优先倾斜一线；是否善于总结一线的生动实践和鲜活经验，运用好基层经验引领发展实践。'},
 {'key': 'performance',
  'label': '工作成效好不好',
  'content': '是否围绕党委中心推进工作，不偏不倚抓贯彻落实；是否在工作中干出成绩、成效显著；是否把创造思维运用于实践工作，形成特色亮点和品牌效应；是否扎根于群众之中，有较高的群众满意度。'}]

TEAM_DIMENSIONS = [{'key': 'political',
  'label': '一看政治站位高不高',
  'content': '是否坚决贯彻执行上级和监狱党委的决策部署，把监狱重点工作作为重大政治任务抓落实；是否在关键时期、重大原则问题上政治立场坚定，政治方向正确；是否具备较强的政治鉴别力和政治敏感性。'},
 {'key': 'integrity',
  'label': '二看道德品行优不优',
  'content': '是否廉洁自律，公正廉明；是否践行社会主义核心价值观，弘扬中华优秀传统美德；是否自觉远离低级趣味，坚决抵制歪风邪气，恪守社会公德、职业道德、家庭美德和个人品德。'},
 {'key': 'responsibility',
  'label': '三看责任担当硬不硬',
  'content': '是否在急难险重任务面前，不讲条件、不打折扣、义不容辞、冲锋在前；是否在困难面前，迎难而上、勇挑重担、力解难题；是否只会被人推着走，不愿主动干；是否关键时刻顶得上、靠得住。'},
 {'key': 'style',
  'label': '四看行为作风正不正',
  'content': '是否坚决杜绝形式主义、官僚主义；是否依靠群众、脚踏实地、稳扎稳打、善作善成；是否人前一个样，人后一个样；是否自觉保持干净的生活圈和社交圈；是否作风正派、公道老实。'},
 {'key': 'thinking',
  'label': '五看工作思路清不清',
  'content': '是否在贯彻上级精神上坚定不移，在落实工作要求上不折不扣；是否结合实际、与时俱进创造性地开展业务工作；是否熟练掌握所在岗位的业务知识，胜任本职岗位职责；是否能团结同事、凝聚人心；是否有拿得下、战必胜的坚定信心和决心。'},
 {'key': 'frontline',
  'label': '六看践行一线实不实',
  'content': '是否做到靠前指挥，深入一线去发现和解决问题；是否践行“一线工作法”，切实把重心力量下沉到基层一线；是否服务好基层一线，千方百计解决一线工作难题，优质资源优先倾斜一线；是否善于总结一线的生动实践和鲜活经验，运用好基层经验引领发展实践。'},
 {'key': 'performance',
  'label': '七看工作成效好不好',
  'content': '是否围绕党委中心推进工作，不偏不倚抓贯彻落实；是否在工作中干出成绩、成效显著；是否把创造思维运用于实践工作，形成特色亮点和品牌效应；是否扎根于群众之中，有较高的群众满意度。'}]

CADRE_TALK_DIMENSIONS = [{'key': 'belief',
  'label': '信念坚定',
  'content': '具有坚定的马克思主义信仰和社会主义共产主义信念，树牢“四个意识”、坚定“四个自信”、做到“两个维护”，对党忠诚，政治敏锐性和政治鉴别力强，加强党的理论武装，遵守党章，对党和组织感情深厚，拥护和贯彻党的路线方针政策等。'},
 {'key': 'serve',
  'label': '为民服务',
  'content': '坚持对人民群众负责的工作原则，有很强的公仆意识和群众观念，密切联系群众，注重倾听群众意见，帮助群众排忧解难，群众认可满意度高，维护群众合法权益，俯下甚至贴近群众等。'},
 {'key': 'diligent',
  'label': '勤政务实',
  'content': '积极投入工作，在工作中精益求精、勤奋奉献，履行好岗位职责，有求真务实的工作作风，从实际出发谋划事业和工作，取得良好的工作实绩等。'},
 {'key': 'courage',
  'label': '敢于担当',
  'content': '敢于直面工作中的问题和矛盾，敢于勇挑重担，敢于担当先锋、主动变革，善于处理棘手问题，敢于承认过失错误，改革攻坚敢于动真碰硬等。'},
 {'key': 'clean',
  'label': '清正廉洁',
  'content': '处事公道不偏袒，不搞一言堂，公私分明，勤俭节约，严格要求家属和身边同志，不利用职务之便谋求私利，积极保持健康的生活，选人用人公道正派等。'}]

TEAM_EVAL_ITEMS = [{'category': '政治思想建设',
  'key': 'political_direction',
  'label': '政治方向',
  'content': '旗帜鲜明讲政治，牢固树立“四个意识”，坚定“四个自信”，践行“两个坚决维护”，在思想上政治上行动上与党中央保持高度一致；严肃党内政治生活；弘扬共产党人价值观；牢记宗旨，心系警察职工，永葆共产党人政治本色。',
  'highlights': ''},
 {'category': '政治思想建设',
  'key': 'ideal_belief',
  'label': '理想信念',
  'content': '坚持用习近平新时代中国特色社会主义思想武装头脑，理想信念坚定。',
  'highlights': ''},
 {'category': '政治思想建设',
  'key': 'work_guidance',
  'label': '业务指导思想',
  'content': '端正性和坚定性，法治意识、目标意识、责任意识，依法治监、行政，理论联系实际，坚持原则，求真务实，科学发展；敢于担当，勇于负责。',
  'highlights': ''},
 {'category': '作风建设',
  'key': 'democratic_centralism',
  'label': '民主集中制',
  'content': '民主意识，坚持民主集中制，一把手民主意识强，班子成员充分发表意见，不存在“家长制”、“一言堂”，不存在议而不决、决而不行；定期开展批评与自我批评，民主生活会质量高；团结协作，分工合理，职责明确；工作制度和议事规则健全；班子整体运行顺畅。',
  'highlights': ''},
 {'category': '作风建设',
  'key': 'personnel',
  'label': '选人用人',
  'content': '坚持党管干部原则，坚持正确选人用人导向，突出政治过硬，匡正选人用人风气；坚持党管人才原则，注重培养教育干部；严格管理干部。',
  'highlights': ''},
 {'category': '作风建设',
  'key': 'lead_by_example',
  'label': '以上率下',
  'content': '遵纪守法；在重要工作、关键时刻的表现；贯彻落实中央“八项规定”精神，坚决反对形式主义、官僚主义、享乐主义和奢靡之风；密切联系警察职工，切实解决实际问题。',
  'highlights': ''},
 {'category': '能力建设',
  'key': 'learning',
  'label': '学习能力',
  'content': '学习意识，学习主动性；完善理论学习制度，运用理论解决实际问题。',
  'highlights': ''},
 {'category': '能力建设',
  'key': 'decision',
  'label': '科学决策能力',
  'content': '自觉性、坚定性、可操作性；依法、民主、科学决策；注重调研，联系实际，突出重点。',
  'highlights': ''},
 {'category': '能力建设',
  'key': 'lawful',
  'label': '依法履职能力',
  'content': '总揽全局，统筹兼顾，协调各方，推进工作力度；充分、正确领会上级决策和政策，及时部署和落实到位的能力；班子整体功能得到充分发挥。',
  'highlights': ''},
 {'category': '能力建设',
  'key': 'safety',
  'label': '维护安全稳定能力',
  'content': '安全首位意识，基础工作扎实，风险防控能力，处置突发事件能力；善于抓班子带队伍，有效发挥班子和队伍的凝聚力、战斗力、向心力、整体合力。',
  'highlights': ''},
 {'category': '能力建设',
  'key': 'sustainable',
  'label': '可持续发展能力',
  'content': '改革意识，创新思维，科学谋划；激发队伍活力，增强发展动力，开拓进取。',
  'highlights': ''},
 {'category': '廉政建设',
  'key': 'clean_work',
  'label': '干净干事',
  'content': '自重、自省、自警、自励；敬畏意识、廉政意识、纪律意识、规矩意识。',
  'highlights': ''},
 {'category': '廉政建设',
  'key': 'main_responsibility',
  'label': '发挥主体作用',
  'content': '落实党风廉政建设责任制，落实廉洁从政的规章制度，构建惩防体系，完善监督制约机制；宣传教育、组织领导、监督检查、率先垂范，发挥表率、统揽、引领、指导作用。',
  'highlights': ''},
 {'category': '工作实绩',
  'key': 'grassroots',
  'label': '基层组织建设',
  'content': '严格落实“三会一课”制度，夯实党的组织基础，坚持围绕中心、服务大局、与时俱进、改革创新，更好地发挥基层党组织战斗堡垒作用和党员的先锋模范作用。',
  'highlights': ''},
 {'category': '工作实绩',
  'key': 'innovation',
  'label': '推动监狱创新可持续发展',
  'content': '深化改革，攻坚克难，推动监狱创新力度；科学制定发展规划，突出主业，有效促改革、谋发展；广阔的发展前景和可持续发展能力。',
  'highlights': ''},
 {'category': '工作实绩',
  'key': 'annual_goals',
  'label': '完成年度目标任务',
  'content': '根据各业务线条下发的年度工作目标确定',
  'highlights': ''}]

TALK_OVERALL = [{'key': 'operation', 'label': '1.对本党支部中层领导班子运行情况的评价'},
 {'key': 'management_supervision', 'label': '2.对本党支部加强干部全方位管理和经常性\n   监督情况的评价'},
 {'key': 'construction', 'label': '3.对本党支部政治思想建设、作风建设、能力建设、廉政建设、工作实绩方面的评价'}]

TALK_ISSUES = [{'key': 'issue_01',
  'label': '（1）坚决维护习近平总书记的核心、全党的核心地位，坚决维护党中央权威和集中统一领导，坚持和加强党的全面领导，执行党的理论和路线方针政策，增强“四个意识”，做到“四个服从”，遵守政治纪律和政治规矩的情况有所不足'},
 {'key': 'issue_02', 'label': '（2）用习近平新时代中国特色社会主义思想武装头脑，坚定理想信念，坚定“四个自信”，不忘初心、牢记使命的情况有所不足'},
 {'key': 'issue_03', 'label': '（3）坚持民主集中制，执行新形势下党内政治生活若干准则，发现和解决自身问题，营造风清气正政治生态的情况有所不足'},
 {'key': 'issue_04', 'label': '（4）践行新时代党的组织路线，贯彻新时期好干部标准，树立正确选人用人导向的情况有所不足'},
 {'key': 'issue_05', 'label': '（5）适应新时代要求、落实党上级和监狱党委决策部署、完成目标任务的能力有所不足'},
 {'key': 'issue_06', 'label': '（6）恪守立党为公、执政为民理念，具有“功成不必在我”精神，以造福人民为最大政绩，真正做到对历史和人民福祉方面有所不足'},
 {'key': 'issue_07', 'label': '（7）在履行职能、服务大局和中心工作和实际成效上有所不足'},
 {'key': 'issue_08', 'label': '（8）在落实新时代党的建设总要求、抓党建工作的实绩上有所不足'},
 {'key': 'issue_09', 'label': '（9）履行管党治党政治责任，加强党风廉政建设，持之以恒正风肃纪，推进反腐败斗争等情况有所不足'},
 {'key': 'issue_10', 'label': '（10）坚持以人民为中心，贯彻党的群众路线，密切联系群众，为群众排忧解难，全心全意为人民服务方面有所不足'},
 {'key': 'issue_11', 'label': '（11）结合实际落实上级和监狱党委工作部署，增强人民获得感、幸福感、安全感方面有所不足'},
 {'key': 'issue_12', 'label': '（12）深入改进作风，落实中央八项规定及其实施细则精神，反对“四风”特别是形式主义、官僚主义方面有所不足'},
 {'key': 'issue_13', 'label': '（13）实事求是，真抓实干，察实情、出实招、办实事、求实效方面有所不足'},
 {'key': 'issue_14', 'label': '（14）干部队伍精神状态不佳或斗争精神有所不足'},
 {'key': 'issue_15', 'label': '（15）存在任人唯亲、搞小圈子等不正之风，坚持五湖四海、任人唯贤有所不足'}]

FORM_META = [
    {
        'key': FormType.ATTACHMENT_2, 'short_label': '自评表',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '中层领导（含团队负责人）各 1 份，纸质+电子。',
    },
    {
        'key': FormType.ATTACHMENT_3, 'short_label': '个人述事',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '与附件2同一人群，中层领导各 1 份。',
    },
    {
        'key': FormType.ATTACHMENT_4, 'short_label': '班子评价',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '每个党支部 1 份，由党支部书记（班子代表）填写，纸质+电子。',
    },
    {
        'key': FormType.ATTACHMENT_5, 'short_label': '支部述事',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '每个党支部 1 份，由党支部书记填写。',
    },
    {
        'key': FormType.ATTACHMENT_6_1, 'short_label': '班子测评（书记）',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '党支部书记各 1 份，会前制作，工作组审核后发放。',
    },
    {
        'key': FormType.ATTACHMENT_6_2, 'short_label': '班子测评（民警职工）',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '本支部民警职工各 1 份，仅纸质。',
    },
    {
        'key': FormType.ATTACHMENT_7_1, 'short_label': '干部测评（正职）',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '党支部书记评正职，各 1 份，纸质+电子。',
    },
    {
        'key': FormType.ATTACHMENT_7_2, 'short_label': '干部测评（副职）',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '党支部书记评副职，各 1 份，纸质+电子。',
    },
    {
        'key': FormType.ATTACHMENT_7_3, 'short_label': '干部测评（团队负责人）',
        'auto_dispatch': False, 'manual_only': True,
        'rule': '附件8未列。网页可填，默认不自动下发，由管理员勾选政工领导。',
    },
    {
        'key': FormType.ATTACHMENT_7_4, 'short_label': '干部测评（本支部）',
        'auto_dispatch': True, 'manual_only': False,
        'rule': '支委与全体民警职工（除支委外）各 1 份；同一模板，填报身份不同。',
    },
    {
        'key': FormType.ATTACHMENT_1, 'short_label': '谈话测评',
        'auto_dispatch': False, 'manual_only': True,
        'rule': '样例表。下发对象由管理员选择。',
    },
]

FORM_META_MAP = {item['key']: item for item in FORM_META}

RULES_TEXT = (
    '附件8规定谁填什么表：附件2/3由中层领导（含团队负责人）填写；附件4/5每个党支部 1 份，'
    '默认下发给党支部书记；附件6-1、7-1、7-2 下发给党支部书记；附件6-2 下发给本支部民警职工；'
    '附件7-4 下发给支委和除支委外的全体民警职工。附件7-3、附件1 不按附件8自动全员下发，需管理员勾选。'
    '被评对象尽量从花名册、组织树带入。提交后只读，管理员可退回重填。'
)


def form_catalog():
    return [
        {
            'key': item['key'],
            'label': FormType(item['key']).label,
            'short_label': item['short_label'],
            'auto_dispatch': item['auto_dispatch'],
            'manual_only': item['manual_only'],
            'rule': item['rule'],
        }
        for item in FORM_META
    ]


def schema_for(form_type):
    return {
        'form_type': form_type,
        'label': FormType(form_type).label if form_type in FormType.values else form_type,
        'self_dimensions': SELF_DIMENSIONS,
        'team_dimensions': TEAM_DIMENSIONS,
        'cadre_talk_dimensions': CADRE_TALK_DIMENSIONS,
        'team_eval_items': TEAM_EVAL_ITEMS,
        'talk_overall': TALK_OVERALL,
        'talk_issues': TALK_ISSUES,
        'self_eval_grades': SELF_EVAL_GRADES,
        'recognition_options': RECOGNITION_OPTIONS,
        'personnel_categories': PERSONNEL_CATEGORIES,
        'matrix_grades': MATRIX_GRADES,
        'talk_grades': TALK_GRADES,
        'roles': ROLES,
        'experience_structures': EXPERIENCE_STRUCTURES,
        'marital_statuses': MARITAL_STATUSES,
    }


def _empty_dim_row(item, extra=None):
    row = {
        'key': item['key'],
        'label': item['label'],
        'content': item.get('content', ''),
        'highlights': '',
        'performance': '',
        'shortcomings': '',
        'grade': '',
    }
    if extra:
        row.update(extra)
    return row


def _score_map(dimensions):
    return {item['key']: '' for item in dimensions}


def default_payload(form_type, context=None):
    context = context or {}
    roster = context.get('roster') or {}
    branch = context.get('branch') or {}
    targets = deepcopy(context.get('targets') or [])

    if form_type == FormType.ATTACHMENT_2:
        return {
            'signature': roster.get('name') or '',
            'self_eval_date': '',
            'unit': roster.get('department') or branch.get('name') or '',
            'name': roster.get('name') or '',
            'position_rank': roster.get('position_label') or '',
            'residence': roster.get('residence') or '',
            'marital_status': '',
            'health': '',
            'current_position_years': roster.get('current_position_years') or '',
            'office_work_years': '',
            'prison_work_years': roster.get('prison_work_years') or '',
            'main_business_lines': roster.get('work_charge') or '',
            'rewards_last_3y': '',
            'punishments_last_3y': '',
            'dimensions': [_empty_dim_row(item) for item in SELF_DIMENSIONS],
            'rectification': '',
            'personal_requests': '',
            'prefill_fields': ['name', 'unit', 'position_rank', 'residence', 'current_position_years', 'main_business_lines'],
        }

    if form_type == FormType.ATTACHMENT_3:
        return {
            'signature': roster.get('name') or '',
            'fill_date': '',
            'name': roster.get('name') or '',
            'gender': roster.get('gender') or '',
            'birth_date': roster.get('birth_date') or '',
            'department_position': roster.get('department_position') or '',
            'current_position_date': roster.get('current_position_date') or '',
            'political_status': roster.get('political_status') or '',
            'items': [{'experience': '', 'key_work': '', 'roles': [], 'details': ''}],
            'prefill_fields': ['name', 'gender', 'birth_date', 'department_position', 'current_position_date', 'political_status'],
        }

    if form_type == FormType.ATTACHMENT_4:
        return {
            'branch_name': branch.get('name') or '',
            'eval_date': '',
            'leadership_current': None,
            'leadership_vacancy': None,
            'team_leader_current': None,
            'team_leader_vacancy': None,
            'experience_structure': '',
            'experience_counts': {'office': None, 'balanced': None, 'prison': None},
            'rectification': '',
            'team_requests': '',
            'adjustment_needed': '',
            'adjustment_suggestion': '',
            'items': [
                {
                    **_empty_dim_row(item),
                    'category': item['category'],
                    'content': item['content'],
                    'highlights': item['highlights'],
                }
                for item in TEAM_EVAL_ITEMS
            ],
            'prefill_fields': ['branch_name'],
        }

    if form_type == FormType.ATTACHMENT_5:
        return {
            'branch_name': branch.get('name') or '',
            'fill_date': '',
            'works': [{
                'title': '',
                'description': '',
                'people': [{'name': '', 'roles': [], 'task_and_role': ''}],
            }],
            'prefill_fields': ['branch_name'],
        }

    if form_type == FormType.ATTACHMENT_6_1:
        return {
            'targets': [
                {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'department': item.get('department') or '',
                    'scores': _score_map(TEAM_DIMENSIONS),
                }
                for item in targets
            ],
            'performance': '',
            'shortcomings': '',
            'other_issues': '',
        }

    if form_type == FormType.ATTACHMENT_6_2:
        target = targets[0] if targets else {'id': branch.get('id'), 'name': branch.get('name') or ''}
        return {
            'branch_name': target.get('name') or branch.get('name') or '',
            'scores': _score_map(TEAM_DIMENSIONS),
            'recognition': '',
            'performance': '',
            'shortcomings': '',
            'other_issues': '',
            'prefill_fields': ['branch_name'],
        }

    if form_type in {FormType.ATTACHMENT_7_1, FormType.ATTACHMENT_7_2, FormType.ATTACHMENT_7_3, FormType.ATTACHMENT_7_4}:
        return {
            'targets': [
                {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'department': item.get('department') or '',
                    'position': item.get('position_label') or item.get('position') or '',
                    'scores': _score_map(TEAM_DIMENSIONS),
                    **({'recognition': ''} if form_type == FormType.ATTACHMENT_7_4 else {}),
                }
                for item in targets
            ],
            'performance': '',
            'shortcomings': '',
            'other_issues': '',
        }

    if form_type == FormType.ATTACHMENT_1:
        return {
            'personnel_category': '',
            'branch_scores': _score_map(CADRE_TALK_DIMENSIONS),
            'branch_name': branch.get('name') or '',
            'overall': [{'key': item['key'], 'label': item['label'], 'grade': ''} for item in TALK_OVERALL],
            'issues': [],
            'other': '',
            'targets': [
                {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'department': item.get('department') or '',
                    'position': item.get('position_label') or item.get('position') or '',
                    'scores': _score_map(CADRE_TALK_DIMENSIONS),
                }
                for item in targets
            ],
            'prefill_fields': ['branch_name'],
        }

    return {}


def merge_payload(form_type, stored, context):
    base = default_payload(form_type, context)
    if not stored:
        return base
    merged = deepcopy(base)
    merged.update(stored)
    if form_type == FormType.ATTACHMENT_1:
        allowed = {row['key'] for row in TALK_OVERALL}
        legacy = [row for row in (stored.get('overall') or []) if row.get('key') not in allowed]
        if legacy:
            merged['legacy_overall'] = deepcopy(stored.get('legacy_overall') or []) + deepcopy(legacy)
        issue_keys = {row['key'] for row in TALK_ISSUES}
        legacy_issues = [key for key in (stored.get('issues') or []) if key not in issue_keys]
        if legacy_issues:
            merged['legacy_issues'] = list(dict.fromkeys((stored.get('legacy_issues') or []) + legacy_issues))
        merged['issues'] = [key for key in (stored.get('issues') or []) if key in issue_keys]
        merged['branch_scores'] = {**base['branch_scores'], **(stored.get('branch_scores') or {})}
    if form_type == FormType.ATTACHMENT_4:
        merged['experience_counts'] = {**base['experience_counts'], **(stored.get('experience_counts') or {})}
    if form_type == FormType.ATTACHMENT_6_2:
        merged['scores'] = {**base['scores'], **(stored.get('scores') or {})}
    if 'dimensions' in base and stored.get('dimensions'):
        merged['dimensions'] = _merge_rows(base['dimensions'], stored['dimensions'], 'key')
    if 'items' in base and form_type == FormType.ATTACHMENT_4 and stored.get('items'):
        merged['items'] = _merge_rows(base['items'], stored['items'], 'key')
    if 'targets' in base:
        merged['targets'] = _merge_targets(base.get('targets') or [], stored.get('targets') or [])
    if 'overall' in base and stored.get('overall'):
        merged['overall'] = _merge_rows(base['overall'], [row for row in stored['overall'] if row.get('key') in {item['key'] for item in TALK_OVERALL}], 'key')
    return merged


def _merge_rows(defaults, stored, key_name):
    stored_map = {row.get(key_name): row for row in stored if isinstance(row, dict)}
    result = []
    for row in defaults:
        extra = stored_map.get(row.get(key_name)) or {}
        merged = deepcopy(row)
        merged.update({k: v for k, v in extra.items() if k not in {'content', 'label', 'category', 'highlights'}})
        result.append(merged)
    extra_keys = [row for row in stored if isinstance(row, dict) and row.get(key_name) not in {r.get(key_name) for r in defaults}]
    result.extend(extra_keys)
    return result


def _merge_targets(defaults, stored):
    stored_map = {}
    for row in stored:
        if not isinstance(row, dict):
            continue
        stored_map[str(row.get('id') or row.get('name') or '')] = row
    result = []
    seen = set()
    for row in defaults:
        key = str(row.get('id') or row.get('name') or '')
        extra = stored_map.get(key) or {}
        merged = deepcopy(row)
        if extra.get('scores'):
            scores = dict(merged.get('scores') or {})
            scores.update(extra['scores'])
            merged['scores'] = scores
        for field in ('performance', 'shortcomings', 'other_issues', 'name', 'department', 'position', 'recognition'):
            if extra.get(field) not in (None, ''):
                merged[field] = extra[field]
        result.append(merged)
        seen.add(key)
    for key, extra in stored_map.items():
        if key and key not in seen:
            result.append(extra)
    return result


def _require(condition, message):
    if not condition:
        raise ValidationError(message)


def validate_payload(form_type, payload, *, strict=False):
    payload = payload or {}
    if not strict:
        return payload

    if form_type == FormType.ATTACHMENT_2:
        _require((payload.get('name') or '').strip(), '请填写姓名。')
        _require((payload.get('unit') or '').strip(), '请填写单位。')
        dims = payload.get('dimensions') or []
        _require(len(dims) >= len(SELF_DIMENSIONS), '请完成七个维度自评。')
        for item in SELF_DIMENSIONS:
            row = next((d for d in dims if d.get('key') == item['key']), None)
            _require(row and row.get('grade') in SELF_EVAL_GRADES, f'请对「{item["label"]}」作出优/良/中/差自评。')
            _require((row.get('performance') or '').strip(), f'请填写「{item["label"]}」现实表现。')

    elif form_type == FormType.ATTACHMENT_3:
        _require((payload.get('name') or '').strip(), '请填写姓名。')
        items = [row for row in (payload.get('items') or []) if isinstance(row, dict)]
        _require(items, '请至少填写一条任职经历/重点工作。')
        for index, row in enumerate(items, start=1):
            _require((row.get('key_work') or row.get('experience') or '').strip(), f'第 {index} 条请填写重点工作或任职经历。')
            _require(isinstance(row.get('roles'), list) and row['roles'] and all(role in ROLES for role in row['roles']), f'第 {index} 条请选择有效的承担角色。')
            _require((row.get('details') or '').strip(), f'第 {index} 条请填写事情详细情况。')

    elif form_type == FormType.ATTACHMENT_4:
        for label, value in [
            ('监区/部门领导现有人数', payload.get('leadership_current')),
            ('监区/部门领导空缺人数', payload.get('leadership_vacancy')),
            ('团队负责人现有人数', payload.get('team_leader_current')),
            ('团队负责人空缺人数', payload.get('team_leader_vacancy')),
            *[(label, (payload.get('experience_counts') or {}).get(key)) for key, label in
              [('office', '长期在机关人数'), ('balanced', '相对均衡人数'), ('prison', '长期在监区人数')]],
        ]:
            if value is not None and value != '':
                _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f'「{label}」须为非负整数。')
        _require((payload.get('branch_name') or '').strip(), '请填写党支部名称。')
        items = payload.get('items') or []
        for spec in TEAM_EVAL_ITEMS:
            row = next((d for d in items if d.get('key') == spec['key']), None)
            _require(row and row.get('grade') in SELF_EVAL_GRADES, f'请对「{spec["label"]}」作出优/良/中/差评价。')
            _require((row.get('performance') or '').strip(), f'请填写「{spec["label"]}」现实表现。')

    elif form_type == FormType.ATTACHMENT_5:
        _require((payload.get('branch_name') or '').strip(), '请填写党支部名称。')
        works = [row for row in (payload.get('works') or []) if isinstance(row, dict) and (row.get('title') or '').strip()]
        _require(works, '请至少填写一条重点工作。')
        for work in works:
            people = [p for p in (work.get('people') or []) if isinstance(p, dict) and (p.get('name') or '').strip()]
            _require(people, f'「{work["title"]}」下请至少填写一名具体人员。')
            for person in people:
                _require(isinstance(person.get('roles'), list) and person['roles'] and all(role in ROLES for role in person['roles']), f'请为 {person.get("name")} 选择有效的承担角色。')
                _require((person.get('task_and_role') or '').strip(), f'请填写 {person.get("name")} 的具体任务和作用发挥。')

    elif form_type == FormType.ATTACHMENT_6_1:
        _validate_matrix(payload.get('targets') or [], TEAM_DIMENSIONS, '党支部')

    elif form_type == FormType.ATTACHMENT_6_2:
        _require((payload.get('branch_name') or '').strip(), '请确认评价的党支部。')
        _validate_scores(payload.get('scores') or {}, TEAM_DIMENSIONS, payload.get('branch_name') or '本支部')
        _require(payload.get('recognition') in RECOGNITION_OPTIONS, '请选择工作认可度。')

    elif form_type in {FormType.ATTACHMENT_7_1, FormType.ATTACHMENT_7_2, FormType.ATTACHMENT_7_3, FormType.ATTACHMENT_7_4}:
        _validate_matrix(payload.get('targets') or [], TEAM_DIMENSIONS, '干部')
        if form_type == FormType.ATTACHMENT_7_4:
            for target in payload.get('targets') or []:
                _require(target.get('recognition') in RECOGNITION_OPTIONS, f'请选择「{target.get("name") or "干部"}」的工作认可度。')

    elif form_type == FormType.ATTACHMENT_1:
        _require(payload.get('personnel_category') in PERSONNEL_CATEGORIES, '请选择人员类别。')
        issues = payload.get('issues') or []
        _require(isinstance(issues, list) and all(key in {item['key'] for item in TALK_ISSUES} for key in issues), '请选择表单列出的主要问题。')
        _validate_scores(payload.get('branch_scores') or {}, CADRE_TALK_DIMENSIONS, '本党支部')
        overall = payload.get('overall') or []
        for spec in TALK_OVERALL:
            row = next((d for d in overall if d.get('key') == spec['key']), None)
            _require(row and row.get('grade') in TALK_GRADES, f'请对「{spec["label"]}」作出评价。')
        _validate_matrix(payload.get('targets') or [], CADRE_TALK_DIMENSIONS, '干部')

    return payload


def _validate_matrix(targets, dimensions, noun):
    _require(targets, f'没有可评价的{noun}名单，请联系管理员。')
    for target in targets:
        name = target.get('name') or noun
        _validate_scores(target.get('scores') or {}, dimensions, name)


def _validate_scores(scores, dimensions, name):
    for item in dimensions:
        _require(scores.get(item['key']) in MATRIX_GRADES, f'请对「{name}」的「{item["label"]}」选择优/良/中/差。')
