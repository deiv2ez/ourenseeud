"""
report_copy.py — Repertorio de frases e consellos para o informe (sen IA).

Cada bloque ten VARIAS variantes; escóllese unha de forma estable segundo a xornada
(mesmo partido → mesmo informe; partidos distintos → varían).

PRINCIPIO DE COHERENCIA (importante):
A UD Ourense de Juan Carballo é un equipo VALENTE, DOMINADOR DO BALÓN e de PRESIÓN ALTA,
tanto en casa como fóra. NON xoga "á contra" nin renuncia a propoñer a domicilio: fóra
axústase o momento da presión e a xestión dos espazos, pero a identidade non cambia.
As frases evitan tópicos que contradigan ese estilo e manteñen coherencia interna.
"""


def _pick(variants: list, seed: int) -> str:
    if not variants:
        return ""
    return variants[seed % len(variants)]


# ---- favor / igualdade ----
FAVOR_CLARO = [
    "Os números colocan á UD Ourense por diante, pero en Primeira Federación ningunha vantaxe se dá por feita: haberá que refrendala no campo.",
    "A UD Ourense parte como favorita. A categoría, porén, obriga a competir cada balón coa mesma intensidade que se o marcador estivese en contra.",
    "As previsións sorrín á UD Ourense. O reto é transformar ese favoritismo en dominio real desde o primeiro minuto.",
]
FAVOR_LEVE = [
    "Lixeira vantaxe para a UD Ourense nun encontro que se prevé axustado: os detalles e a eficacia nas áreas marcarán a diferenza.",
    "A balanza inclínase levemente do lado ourensán, nun choque parello onde a xestión dos momentos será decisiva.",
    "A UD Ourense parte un chisco por diante, pero a igualdade da categoría fai que nada estea decidido de antemán.",
]
FAVOR_IGUAL = [
    "O partido preséntase moi igualado, sen un favorito claro: será cuestión de detalles e de quen impoña antes o seu plan.",
    "Equilibrio máximo nas previsións. Calquera desenlace entra dentro do previsible, así que a execución pesará máis ca o guión.",
    "Choque de pronóstico aberto. A UD Ourense terá que gañar o partido co seu xogo, sen agardar a que o rival llo conceda.",
]
FAVOR_CONTRA = [
    "O rival parte como favorito sobre o papel, pero a proposta ourensá —dominio e presión— pode darlle a volta ao guión se se executa con acerto.",
    "As previsións non son favorables sobre o papel; será clave manter a identidade, competir con personalidade e ser eficaces nas ocasións que se xeren.",
    "O pronóstico non acompaña, aínda que a categoría demostra cada semana que o favoritismo previo importa pouco cando se compite con orde e ambición.",
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
    "reforza a proposta dominadora e de presión alta, coa afección empuxando desde o inicio.",
    "convida a asumir a iniciativa e a someter o rival preto da súa área, fieis ao estilo do equipo.",
    "anima a impoñer o ritmo desde o primeiro minuto e a facer valer o factor campo.",
]
VENUE_AWAY = [
    "pide manter a identidade dominadora, axustando os tempos da presión para escoller ben cando apertar.",
    "convida a propoñer igual que na casa, medindo os momentos para non quedar expostos nas transicións.",
    "aconsella sostener a proposta con criterio, alternando dominio e control para xestionar os espazos.",
]


def venue_text(is_home: bool, seed: int) -> str:
    return _pick(VENUE_HOME if is_home else VENUE_AWAY, seed)


# ---- claves ofensivas ----
KEY_RIVAL_CONCEDE = [
    "O rival concede máis ocasións das que o seu marcador suxire: a presión alta tras perda pode provocar erros na súa saída de balón.",
    "A defensa rival amosa fisuras baixo presión; recuperar arriba e atacar rápido debería traducirse en chegadas claras.",
    "O rival sofre cando o aprietan na saída: insistir na presión coordinada abrirá vías directas cara á súa portería.",
]
KEY_RIVAL_XGA = [
    "Concede un volume alto de ocasións: atacar con verticalidade e xerar superioridades polas bandas.",
    "O rival permite chegadas con frecuencia; convén insistir polas bandas e atacar o segundo pau con xente.",
    "As costas dos seus laterais son un territorio fértil: desmarques ao espazo e centros con presenza na área.",
]
KEY_FINISH = [
    "Manter o volume de tiro dentro da área: a eficacia é decisiva nunha liga tan igualada.",
    "Priorizar tiros de calidade dentro da área fronte a disparos afastados de baixa probabilidade.",
    "Traducir o dominio en ocasións claras: chegar máis non serve se non se remata con criterio.",
]


# ---- que evitar ----
KEYS_AGAINST = [
    [
        "Coidar as perdas no primeiro terzo: un equipo que domina expón espazos á espalda que hai que cubrir con rapidez.",
        "Atención ás segundas xogadas e ao balón parado, onde os partidos igualados adoitan decidirse.",
    ],
    [
        "Vixiar os equilibrios cando o equipo se volca ao ataque: as coberturas dos medios deben chegar sempre.",
        "Extremar a concentración nas accións a balón parado en defensa, un detalle que marca a diferenza na categoría.",
    ],
    [
        "Non precipitar a presión de forma descoordinada: se se rompe a liña, o rival atopará espazos para saír.",
        "Manter a orde nos repregues tras perda para que o dominio non se converta en fraxilidade defensiva.",
    ],
]


def keys_against(seed: int) -> list:
    return KEYS_AGAINST[seed % len(KEYS_AGAINST)]


# ---- análise casa/fóra ----
VENUE_ANALYSIS_HOME = [
    ("Xogando en casa, o equipo pode asumir a iniciativa e someter o rival preto da súa área desde o primeiro minuto. "
     "A clave estará en transformar o dominio do balón en ocasións claras, sen impacientarse se o rival se pecha atrás."),
    ("No seu campo, a UD Ourense debe impoñer o seu ritmo e a súa presión alta, coa afección como aliada. "
     "Nunha liga tan parella, a paciencia para atopar os espazos e a eficacia nas áreas serán determinantes."),
    ("Na casa, o plan pasa por dominar o balón e obrigar o rival a defenderse lonxe da súa portería. "
     "A xestión dos tempos —cando acelerar e cando sosterlo— definirá a fluidez do ataque."),
]
VENUE_ANALYSIS_AWAY = [
    ("A domicilio, a UD Ourense non renuncia á súa identidade: dominar e presionar, pero escollendo con criterio os momentos de máxima intensidade. "
     "O control do balón será a mellor ferramenta para restarlle chegadas ao rival e xestionar o partido."),
    ("Fóra da casa, o equipo mantén a súa proposta ofensiva medindo os tempos para non quedar exposto nas transicións. "
     "Sostener o balón nos momentos de dúbida axudará a apagar o pulo local e a construír as súas propias ocasións."),
    ("Como visitante, a chave é competir coa mesma personalidade de sempre, alternando dominio e control. "
     "Un equipo que propón e presiona con orde pode gañar en calquera campo se mantén a concentración os noventa minutos."),
]


def venue_analysis(is_home: bool, seed: int) -> str:
    return _pick(VENUE_ANALYSIS_HOME if is_home else VENUE_ANALYSIS_AWAY, seed)


# ---- escenarios ----
SCENARIO_LEAD = [
    "Cun gol a favor, o rival adiantará liñas e abriranse espazos: é o momento de xestionar o balón con criterio e buscar o segundo, sen descoidar os equilibrios.",
    "Cun tanto de vantaxe, convén sostener o balón, obrigar o rival a perseguir e castigar con calma os ocos que deixe ao arriscar.",
    "Coa dianteira no marcador, o dominio do xogo debe servir para adormecer o partido e atacar os espazos que o rival deixe ao volcarse.",
]
SCENARIO_BEHIND = [
    "Se o marcador é adverso, manter a proposta e a calma: o equipo xera ocasións abondas para remontar, pero sen precipitarse nin perder a orde.",
    "Cun resultado en contra, a paciencia e a insistencia no plan son a mellor arma; forzar de máis só rompe os equilibrios sen crear perigo real.",
    "Se se vai por detrás, a chave é sostener a identidade: dominar, xerar volume de ataque e confiar en que a eficacia acabe chegando.",
]


def scenario_lead(seed: int) -> str:
    return _pick(SCENARIO_LEAD, seed)


def scenario_behind(seed: int) -> str:
    return _pick(SCENARIO_BEHIND, seed)


# ---- consellos ----
ADVICE_SETS = [
    [
        "Presión alta coordinada tras perda no campo rival: a vía máis directa para recuperar cerca da portería contraria.",
        "Atacar as bandas buscando superioridades para abastecer o punta con centros e chegadas de segunda liña.",
        "Coberturas rápidas dos medios centros para tapar o espazo á espalda cando o equipo se volca ao ataque.",
    ],
    [
        "Intensidade na presión tras perda: recuperar arriba para xerar ocasións inmediatas sen dar respiro á saída rival.",
        "Buscar as costas dos laterais rivais con desmarques ao espazo e cambios de orientación.",
        "Equilibrio no medio campo: un pivote atento ás segundas xogadas para sostener o dominio sen expoñerse.",
    ],
    [
        "Dominar o balón con propósito: circular rápido para mover o bloque rival e atopar a fenda no momento xusto.",
        "Presenza na área: chegar con xente ao remate para transformar o dominio territorial en ocasións claras.",
        "Concentración no balón parado defensivo, onde os partidos igualados da categoría adoitan decidirse.",
    ],
]


def advice(seed: int) -> list:
    return ADVICE_SETS[seed % len(ADVICE_SETS)]
