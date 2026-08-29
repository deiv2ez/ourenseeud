"""
report_copy.py — Repertorio de frases e consellos para o informe (sen IA).

Cada bloque ten VARIAS variantes; escóllese unha de forma estable segundo a xornada
(mesmo partido → mesmo informe; partidos distintos → varían). Así os informes das
distintas xornadas non se repiten palabra por palabra.

As frases que dependen dos DATOS (ex. rival que concede moito) escóllense por lóxica,
non ao chou; as variantes son para o mesmo diagnóstico redactado de xeitos distintos.
"""


def _pick(variants: list, seed: int) -> str:
    """Escolle unha variante de forma estable segundo o seed (xornada)."""
    if not variants:
        return ""
    return variants[seed % len(variants)]


# ---- favor / igualdade (segundo a diferenza de probabilidade) ----
FAVOR_CLARO = [
    "A UD Ourense parte como favorita, aínda que en Primeira Federación ningunha vantaxe está garantida.",
    "O favoritismo recae na UD Ourense, mais non hai rival pequeno nesta liga tan esixente.",
    "Sobre o papel o noso equipo é superior; con todo, tocará demostralo sobre o terreo de xogo.",
    "A condición de claro favorito é para a UD Ourense, aínda que a relaxación está terminantemente prohibida.",
    "As estatísticas avalan á UD Ourense como principal candidata á vitoria, pero a competición esixe máximo rigor.",
    "Todo apunta a un triunfo ourensán, sempre que se manteña a intensidade dende o asubío inicial.",
    "A UD ten todas as de gañar, aínda que a Primeira Federación sempre castiga calquera exceso de confianza.",
    "Pronóstico moi favorable para a UD Ourense, que deberá facer valer a súa teórica superioridade.",
    "O noso conxunto é claro favorito neste encontro; a clave será impor o noso xogo desde o primeiro minuto.",
    "A nivel estatístico a UD Ourense domina as previsións, mais os encontros hai que traballalos ata o final.",
    "Cos datos na man, a UD parte con ampla vantaxe e está obrigada a confirmar as boas expectativas.",
    "Ampla marxe de favoritismo para os ourensáns nun duelo onde non se poden permitir os despistes.",
    "O equipo preséntase con todo ao seu favor para sumar os tres puntos, pero sen subestimar o opoñente.",
    "O cartel de favorito lévao a UD Ourense de forma indiscutible; porén, o esforzo e a concentración non se negocian."
    "Os números colocan á UD Ourense por diante, pero a categoría obriga a competir cada balón.",
]
FAVOR_LEVE = [
    "A UD Ourense parte lixeiramente favorita, nunha categoría moi igualada onde os detalles deciden.",
    "As previsións dan unha pequena marxe á UD Ourense, mais o partido apunta a ser moi competido.",
    "Lixeiro favoritismo para o noso equipo nun choque onde a concentración marcará o devir dos puntos.",
    "Partimos cunha leve vantaxe teórica, aínda que a máxima igualdade da competición non permite relaxacións.",
    "O cadro ourensán é lixeiramente favorito, pero o equilibrio de forzas augura un partido de poder a poder.",
    "Hai unha sutil inclinación a favor da UD Ourense nun duelo que se definirá polas pequenas marxes.",
    "Levamos a etiqueta de lixeiros favoritos, mais haberá que suar moito para impoñernos no marcador.",
    "Un chisco de vantaxe inicial para a UD, que terá que madurar o partido se quere asegurar o resultado.",
    "Malia o lixeiro favoritismo local, a Primeira Federación non adoita perdoar a falta de intensidade.",
    "As cotas dan un pequeno respiro ao noso favor, aínda que o enfrontamento será previsiblemente trabado.",
    "Favoritismo leve para a UD Ourense nun contexto onde calquera erro mínimo pódese pagar moi caro.",
    "A balanza inclínase un chisco ao noso carón, pero tocará baixar ao barro para certificar a vitoria.",
    "Vantaxe marxinal nas previsións para o equipo ourensán nun duelo de máxima esixencia táctica.",
    "Pequeno paso por diante no prognóstico para a UD, conscientes de que o rival non porá as cousas doadas."
    "Lixeira vantaxe para a UD Ourense nun encontro que se prevé axustado de principio a fin.",
]
FAVOR_IGUAL = [
    "O partido preséntase moi igualado, sen un favorito claro: será cuestión de detalles.",
    "O partido preséntase moi igualado, sen un favorito claro: será cuestión de detalles.",
    "Equilibrio máximo nas previsións; calquera desenlace entra dentro do previsible.",
    "Non hai un favorito claro neste enfrontamento: as forzas están sumamente parellas.",
    "Igualdade absoluta na previa do encontro, onde o vencedor será quen cometa menos erros.",
    "As probabilidades non decantan a balanza; agardamos un choque moi nivelado e táctico.",
    "Duelo sen dominador claro a priori, o que converte o acerto nas áreas en algo vital.",
    "Todo pode pasar nun partido onde ambos os equipos parten coas mesmas opcións de éxito.",
    "O choque albíscase moi disputado, sen superioridade clara para ningún dos dous bandos.",
    "Predición de máxima igualdade: a vitoria caerá do lado do equipo que xestione mellor os nervios.",
    "Prevese un duelo de igual a igual, coas espadas no alto e sen favoritos nas apostas.",
    "Partido de prognóstico reservado, calquera detalle illado pode desequilibrar o marcador.",
    "O equilibrio de forzas é total, forzando a ambos os equipos a ofrecer a súa mellor versión.",
    "Duelo moi axustado sen marxe para o erro; as estatísticas non dan vantaxe a ninguén.",
    "Choque de trens onde non hai un claro aspirante a levar os puntos de forma doada.",
    "A balanza está totalmente equilibrada; un encontro para os afeccionados á táctica e á tensión."
    "Equilibrio máximo nas previsións; calquera desenlace entra dentro do previsible.",
]
FAVOR_CONTRA = [
    "O rival parte como favorito, así que tocará competir ao límite e ser eficaces nas poucas ocasións.",
    "Eles asumen o cartel de favoritos, pero a UD Ourense buscará facer dano desde a solidez defensiva.",
    "O prognóstico está na nosa contra; será vital xogar cunha gran concentración e castigar á contra.",
    "O equipo local non parte como favorito, o que resta presión pero esixe un traballo impecable.",
    "Estatísticas en contra para a UD Ourense, que deberá aproveitar o factor sorpresa para sumar.",
    "O rival ten as de gañar; resistir o embate inicial será clave para ter opcións ao final.",
    "Temos todo en contra nos números, polo que a eficacia nas nosas chegadas debe ser do cen por cen.",
    "Enfrontámonos a un favorito claro, obrigándonos a facer o noso partido máis completo da tempada.",
    "As previsións son adversas, mais o equipo debe usar a orde táctica como principal arma de defensa.",
    "Non partimos con vantaxe, así que haberá que maximizar cada balón parado e transición ofensiva.",
    "O adversario ten a obriga de gañar polo seu favoritismo; debemos xogar con esa ansiedade.",
    "Papel de \'tapados\' para a UD Ourense neste choque, onde puntuar pasa por minimizar os fallos.",
    "Choque complexo con prognóstico en contra, pero a Primeira Federación permite sorpresas en cada xornada.",
    "Temos os prognósticos en contra; a resiliencia e a orde serán os nosos mellores aliados hoxe."
    "As previsións non son favorables sobre o papel; haberá que dar a sorpresa con orde e acerto.",
]


def favor_text(pw: int, pl: int, seed: int) -> str:
    if pw >= pl + 12:
        return _pick(FAVOR_CLARO, seed)
    if pw > pl + 4:
        return _pick(FAVOR_LEVE, seed)
    if abs(pw - pl) <= 4:
        return _pick(FAVOR_IGUAL, seed)
    return _pick(FAVOR_CONTRA, seed)


# ---- contexto casa / fóra ----
VENUE_HOME = [
    "reforza a proposta dominadora e de presión alta do equipo.",
    "espertea a necesidade de levar o peso do encontro diante da afección.",
    "dá azos ao equipo para buscar roubar en campo contrario dende o asubío inicial.",
    "motiva aos xogadores a despregar un fútbol máis ambicioso e coral.",
    "debería axudar a impoñer o ritmo de xogo e controlar os tempos do partido.",
    "empurra ao conxunto ourensán a encerrar ao adversario na súa propia metade.",
    "fai que a presión tras perda sexa aínda máis intensa para o afogo rival.",
    "esixe unha versión valente, con protagonismo co balón e profundidade nas bandas.",
    "converte o noso campo nun fortín onde é crucial mandar desde o principio.",
    "ofrece o escenario ideal para someter ao rival a base de posesións longas.",
    "anima a despregar unha estratexia marcadamente ofensiva e proactiva.",
    "obriga a ser o equipo que propoña máis para abrir a lata canto antes.",
    "permite ao equipo xogar con máis confianza para facer recuar a defensa visitante.",
    "invita a ser agresivos sen balón para instalarse permanentemente no campo rival."
    "convida a asumir a iniciativa e a someter o rival preto da súa área.",
]
VENUE_AWAY = [
    "obriga a medir os tempos da presión para non quedar expostos ás transicións.",
    "require xogar con máis cautela, agardando o momento xusto para golpear.",
    "fai indispensable unha defensa sólida e xuntar as liñas no noso campo.",
    "demanda pragmatismo e intelixencia para non caer nas trampas do equipo local.",
    "recomenda repregamentos intensivos antes que presións suicidas fóra da casa.",
    "esixe minimizar os riscos na saída do balón para non ceder ocasións doadas.",
    "condiciona ao equipo a estar moi pendente das vixilancias defensivas.",
    "pide unha versión máis rochosa do equipo, penalizando os erros locais.",
    "implica saber sufrir por momentos e castigar calquera espazo á contra.",
    "suxire unha formulación onde asegurar a portería a cero sexa a prioridade absoluta.",
    "obriga a madurar os partidos desde o repregamento e a seguridade atrás.",
    "aconsella darlle máis importancia ao bloque defensivo que ás aventuras illadas en ataque.",
    "sinala que a orde táctica debe primar sobre os alardes ofensivos.",
    "xustifica ceder a iniciativa ao rival en certas fases para aproveitar espazos ás súas costas."
    "aconsella un equilibrio maior entre a ambición e a orde defensiva.",
]


def venue_text(is_home: bool, seed: int) -> str:
    return _pick(VENUE_HOME if is_home else VENUE_AWAY, seed)


# ---- claves ofensivas (segundo debilidades do rival) ----
KEY_RIVAL_CONCEDE = [
    "O rival concede máis ocasións das que o seu marcador suxire: a presión alta tras perda pode provocar erros na súa saída de balón.",
    "Deixan espazos atrás doadamente: castigar eses ocos con transicións lixeiras será fundamental.",
    "Permiten moitos achegamentos; abonda con ter fluidez na zona de tres cuartos para xerar perigo.",
    "Teñen debilidades defensivas patentes: incidir nesa eiva pode darnos o partido rapidamente.",
    "O rival adoita sufrir na contención; cargar o xogo polas súas zonas febles achegaranos ao gol.",
    "Conceden espazos entre liñas: os nosos mediapuntas deben aproveitar esa fenda para filtrar pases.",
    "O oponente ten carencias cando o premen alto; roubar preto da súa área é a chave.",
    "A súa zaga comete erros de concentración: hai que apertar a saída de balón para forzalos.",
    "Sufren defendendo centros laterais: poboar a área e desbordar polas ás dará os seus froitos.",
    "É un conxunto vulnerable en transicións; saír con velocidade tras recuperación faralles moito dano.",
    "A estatística di que permiten moitos tiros; a premisa é cargar a área e probar a portería.",
    "Son pouco contundentes na marca; gañar os duelos individuais permitiríanos pisar área con claridade.",
    "Os seus centrais perden as costas a miúdo; buscar desmarques de ruptura será o camiño.",
    "Conceden demasiadas facilidades atrás; manter un bo ritmo ofensivo será suficiente para crear oportunidades."
    "A defensa rival amosa fisuras; recuperar arriba e atacar rápido debería traducirse en ocasións.",
]
KEY_RIVAL_XGA = [
    "Concede bastantes ocasións: atacar con verticalidade e superioridades polas bandas.",
    "O xG en contra do opoñente é alto: debemos finalizar xogadas de xeito constante para atopar a rede.",
    "Os números sinalan que reciben perigo con facilidade; pisar área con moitos efectivos é imprescindible.",
    "Permiten un gran número de disparos por partido; hai que armar o tiro á menor oportunidade.",
    "Acumulan un índice de goles esperados en contra elevado; explorar as súas costas asegurarálle traballo ao seu porteiro.",
    "As métricas defensivas do rival son frouxas: atacar polo centro para aproveitar os seus ocos.",
    "Teñen problemas para reducir o perigo nas súas proximidades; xerar triangulacións rápidas será a vía do éxito.",
    "A súa alta concesión de xG suxire centrarse en finalizacións limpas en lugar de tiros forzados.",
    "Ofrecen facilidades que disparan o xG do adversario; hai que penalizar a súa lentitude no repregamento.",
    "O rival sofre coas fendas na súa zaga; potenciar a asociación no último terzo achegaranos aos tantos.",
    "Reciben moitos tiros dende zonas perigosas; os nosos atacantes deben perfilarse ben ao bordo da área.",
    "Deixan demasiadas fendas abertas; a amplitude e a circulación rápida farán subir o noso xG hoxe.",
    "Un xG rival tan alto indica que teremos as nosas; só falta manter a cabeza fría na definición.",
    "A fraqueza do rival á hora de evitar ocasións obriga ao noso equipo a ser agresivo de face a porta."
    "O volume de ocasións que permite o rival convida a insistir polas bandas e buscar o segundo pau.",
]
KEY_FINISH = [
    "Manter o volume de tiro dentro da área; a eficacia é decisiva nunha liga tan igualada.",
    "Priorizar tiros de calidade dentro da área fronte a disparos afastados de baixa probabilidade.",
    "Achegar o balón aos nosos finalizadores na zona perigosa para evitar remates desesperados.",
    "Ter calma nos últimos metros: un pase extra pode asegurar unha ocasión manifesta de gol.",
    "Maximizar a rendibilidade dos achegamentos; na Primeira Federación o que perdoa adoita pagalo.",
    "Evitar precipitacións á hora de chutar; construír a xogada ata atopar a vantaxe limpa.",
    "Fuxir de disparos afastados sen marxe de éxito e apostar pola incursión nas inmediacións da portería.",
    "A contundencia na área marcará o encontro; precisamos precisión clínica diante do gardameta.",
    "Paciencia para xerar a fenda: vale máis un bo remate na área pequena que cinco tiros desde a frontal.",
    "Transformar a posesión en finalizacións claras, cargando con efectivos o corazón da área.",
    "A xestión dos últimos pases será capital para converter o dominio en tiros de alto valor (xG).",
    "Garantir remates limpos evitando o tráfico de defensores; a mobilidade na área será diferencial.",
    "O partido decidirase no acerto: afinar a puntería nas poucas ocasións claras será imprescindible.",
    "Os dianteiros deberán atopar os espazos baleiros dentro do caixón para asegurar tiros sen oposición.",
    "Optimizar a selección de tiro; elixir ben o momento de disparar aumentará substancialmente as opcións de gañar."
    "Priorizar tiros de calidade dentro da área fronte a disparos afastados de baixa probabilidade.",
]


# ---- que evitar ----
KEYS_AGAINST = [
    [
        "Non deixar espazos á espalda: a proposta ofensiva expón o equipo a transicións rápidas.",
        "Coidar as perdas no primeiro terzo e as segundas xogadas a balón parado.",
    ],
    [
        "Protexer as costas dos centrais: envorcarse en ataque facilita os contragolpes do rival.",
        "Evitar perdas na saída de balón e manter a concentración nas xogadas de estratexia.",
    ],
    [
        "Garantir un bo repregamento defensivo: calquera erro na circulación pode ser letal á contra.",
        "Ser contundentes nos rexeites e vixiar de preto as marcas nos córners e faltas laterais.",
    ],
    [
        "Pechar os ocos no retorno defensivo: a nosa ambición ofensiva non debe desprotexer ao porteiro.",
        "Minimizar os erros non forzados no medio campo e gañar os duelos aéreos a balón parado.",
    ],
    [
        "Manter a liña defensiva atenta ás rupturas: un equipo tan adiantado asume riscos nas transicións.",
        "Fuxir de faltas innecesarias preto da nosa área e ser rigorosos na saída desde atrás.",
    ],
    [
        "Vixiar a espalda da defensa: cada perda no ataque pode converterse nunha contra perigosa.",
        "Extremar a atención nas accións a balón parado, onde os partidos igualados adoitan decidirse.",
    ],
]


def keys_against(seed: int) -> list:
    return KEYS_AGAINST[seed % len(KEYS_AGAINST)]


# ---- análise casa/fóra ----
VENUE_ANALYSIS_HOME = [
    ("Xogando en casa, o equipo pode asumir a iniciativa e someter o rival preto da súa área. "
     "A igualdade da categoría fai que os detalles e a eficacia marquen a diferenza."),
    ("Co apoio do noso público, toca levar o peso do partido e afogar o rival no seu campo. "
     "Nun escenario tan competido, materializar as ocasións marcará o destino dos puntos."),
    ("Sendo locais, a UD Ourense ten a responsabilidade de mandar co balón e pisar área con frecuencia. "
     "O acerto de cara a porta acabará decidindo un choque que se prevé intenso."),
    ("Na nosa feuda, o equipo ten que ser protagonista e facer recuar ao adversario a base de ritmo. "
     "Os rendementos nas áreas serán vitais para decantar a balanza."),
    ("Xogando en O Couto, a proposta debe ser ofensiva e dominadora desde o asubío inicial. "
     "A pegada no último terzo ditará sentenza nunha liga onde non se regala nada."),
    ("No seu campo, a UD Ourense debe impoñer o seu ritmo desde o primeiro minuto. "
     "Nunha liga tan parella, a eficacia nas áreas será determinante."),
]
VENUE_ANALYSIS_AWAY = [
    ("Fóra da casa, convén equilibrar a proposta e medir a presión para non quedar expostos. "
     "A paciencia e o acerto nos momentos clave serán fundamentais."),
    ("Lonxe do noso estadio, a orde e a solidariedade defensiva deben ser innegociables. "
     "Saber sufrir sen balón e castigar ao contragolpe achegaranos ao obxectivo."),
    ("A domicilio, convén amosar unha versión máis pragmática e minimizar os riscos na construción. "
     "A eficacia nas transicións rápidas será a nosa mellor arma."),
    ("Actuando como visitantes, o equipo precisa xestionar ben os tempos e pechar espazos por dentro. "
     "A paciencia e a precisión nos últimos metros decidirán a nosa sorte."),
    ("Como forasteiros, a prioridade pasa por ser un bloque sólido e difícil de superar. "
     "Aproveitar as perdas do rival con saídas vertixinosas será a chave para puntuar."),
    ("A domicilio, o equipo debe competir con orde e escoller ben cando apertar. "
     "Aproveitar as transicións pode ser a vía máis rendible."),
]


def venue_analysis(is_home: bool, seed: int) -> str:
    return _pick(VENUE_ANALYSIS_HOME if is_home else VENUE_ANALYSIS_AWAY, seed)


# ---- escenarios (empezan con maiúscula) ----
SCENARIO_LEAD = [
    "Cun gol a favor, o rival adiantará liñas e abriranse espazos para as transicións vertixinosas; xestionar o balón e buscar o segundo sen descoidar as contras.",
    "Con vantaxe no luminoso, o rival deixará máis ocos na súa busca do empate; é o momento de asegurar o pase e saír con velocidade para pechar o partido.",
    "Ao ir gañando, o adversario asumirá máis riscos e desprotexerá a súa defensa; xestionar a posesión con intelixencia e golpear á contra será fundamental.",
    "Cun resultado favorable, tocará aproveitar a ansiedade do equipo contrario, atopando espazos nas costas da súa zaga sen perder a orde atrás.",
    "Co marcador a favor, a clave reside en dominar o tempo do partido e atraer a presión para atopar liñas de pase que nos permitan ampliar a diferenza.",
    "Cun tanto de vantaxe, convén manter a calma, mover o balón e castigar os espazos que deixe un rival obrigado a arriscar.",
]
SCENARIO_BEHIND = [
    "Manter a calma e a proposta: o equipo xera ocasións abondas para remontar, pero sen precipitarse nin descoidar a cobertura.",
    "Co marcador en contra, prohibido caer na precipitación; o equipo ten fútbol suficiente para darlle a volta atacando con criterio e orde.",
    "Perdendo, a cabeza fría é o noso mellor aliado; hai que seguir madurando as xogadas e evitar que a présa nos faga vulnerables ás transicións rivais.",
    "Se imos por detrás, toca manter a paciencia e mover ao rival para atopar fendas. Volcarse sen sentido só facilitaría as súas contras.",
    "Ante a adversidade no taboleiro, a orde táctica non se negocia; chegar ao empate require fluidez na circulación e non descoidar a defensa do noso porteiro.",
    "Manter a orde e a paciencia se o marcador é adverso; forzar en exceso só favorece as contras do rival.",
]


def scenario_lead(seed: int) -> str:
    return _pick(SCENARIO_LEAD, seed)


def scenario_behind(seed: int) -> str:
    return _pick(SCENARIO_BEHIND, seed)


# ---- consellos ----
ADVICE_SETS = [
    [
        "Presión alta coordinada tras perda no campo rival: a vía máis directa para recuperar cerca da portería contraria.",
        "Atacar as bandas buscando superioridades para abastecer o punta.",
        "Coberturas rápidas dos medios centros para tapar o espazo á espalda nas transicións.",
    ],
    [
        "Saltar á presión en bloque nada máis perder o balón para asfixiar a construción do rival.",
        "Cargar a área con moitos efectivos cada vez que o balón chegue ás bandas.",
        "Manter as liñas moi xuntas no repregamento para non deixar osíxeno aos seus mediapuntas.",
    ],
    [
        "Ser moi agresivos nos duelos individuais en campo contrario para forzar erros na saída.",
        "Fomentar as asociacións en curto por dentro para despois abrir o xogo ás ás.",
        "Vixilancias defensivas constantes dos centrais sobre o seu dianteiro de referencia.",
    ],
    [
        "Pechar as liñas de pase polo centro para obrigar ao rival a xogar por fóra e roubar.",
        "Empregar os desdobramentos dos laterais para xerar superioridades no último terzo.",
        "Estar moi concentrados nas segundas xogadas, fundamentais para facerse co control do medio.",
    ],
    [
        "Activar a recuperación tras perda de forma instantánea, sen darlles tempo a pensar.",
        "Buscar a ruptura constante ao espazo para estirar a defensa e xerar ocos entre liñas.",
        "Asegurar as coberturas dos laterais cando suban ao ataque para non quedar expostos.",
    ],
    [
        "Intensidade na presión tras perda: recuperar arriba para xerar ocasións inmediatas.",
        "Buscar as costas dos laterais rivais con desmarques e cambios de orientación.",
        "Equilibrio no medio campo: un pivote atento ás segundas xogadas e ás contras.",
    ],
]


def advice(seed: int) -> list:
    return ADVICE_SETS[seed % len(ADVICE_SETS)]
