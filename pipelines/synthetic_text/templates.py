"""High-entropy template libraries for synthetic postpartum narrative generation.

Organized into three thematic sections:
1. Household structure, children, and everyday domestic routines.
2. Infant care, feeding routines, and general responsibilities.
3. Sleep windows, rest, and practical family support.

SCIENTIFIC INTEGRITY NOTICE:
All templates are structured as neutral third-person contextual observations.
They contain zero diagnostic claims, zero medical labels, zero clinical measurements,
and zero authentic patient quotations.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np

# =============================================================================
# THEME 1: Household Structure, Children, and Everyday Routines
# =============================================================================

# Sentence 1: Living Arrangement and Household Size
LIVING_ARRANGEMENTS: Dict[Tuple[str, str], List[str]] = {
    ("Nuclear", "2 to 5"): [
        "The participant resides in a nuclear household consisting of two to five family members.",
        "Living in a nuclear family arrangement, the household comprises between two and five individuals.",
        "Within a nuclear domestic setting, daily living involves two to five household members.",
        "Daily family activities are organized in a nuclear household of two to five members.",
        "The home environment is structured around a nuclear family unit of two to five individuals.",
    ],
    ("Nuclear", "6 to 8"): [
        "The participant lives in a nuclear family structure comprising six to eight household members.",
        "Situated in a nuclear domestic arrangement, the home accommodates six to eight family members.",
        "Daily routines take place within a nuclear household consisting of six to eight individuals.",
        "Her domestic environment is organized around a nuclear family setting of six to eight members.",
        "Living in a nuclear family unit, the household includes six to eight individuals sharing the residence.",
    ],
    ("Nuclear", "9 or more"): [
        "The participant resides in a nuclear household accommodating nine or more family members.",
        "Daily home life is situated within a sizable nuclear family structure of nine or more individuals.",
        "Her domestic environment consists of a large nuclear family household comprising nine or more members.",
        "Within a nuclear family arrangement, daily routines involve nine or more household members.",
        "The domestic setting is organized around a nuclear family of nine or more individuals under one roof.",
    ],
    ("Joint", "2 to 5"): [
        "The participant lives in a joint family arrangement consisting of two to five household members.",
        "Residing in a joint domestic setting, daily routines involve two to five extended family members.",
        "Her home life is organized within a joint family structure comprising two to five individuals.",
        "Within a joint family environment, the residence is shared among two to five household members.",
        "Daily domestic activities are situated in a joint family arrangement of two to five members.",
    ],
    ("Joint", "6 to 8"): [
        "The participant resides in an extended joint family household of six to eight members.",
        "Living in a joint family structure, the home includes six to eight relatives sharing daily routines.",
        "Her domestic environment is centered in an active joint household of six to eight family members.",
        "Within an extended joint family arrangement, daily life is shared among six to eight relatives.",
        "Daily household activities are organized around a joint family setting of six to eight individuals.",
    ],
    ("Joint", "9 or more"): [
        "The participant lives in a large joint family household accommodating nine or more members.",
        "Residing in an extended joint family structure, daily living involves nine or more relatives.",
        "Her domestic environment comprises a multigenerational joint household of nine or more individuals.",
        "Within a large joint family arrangement, daily routines are shared among nine or more relatives.",
        "The home setting is centered in an extensive joint family household of nine or more members.",
    ],
}

# Sentence 2: Parity and Sibling Dynamics
PARITY_TEMPLATES: Dict[str, List[str]] = {
    "One": [
        "As a first-time mother, her daily routines center entirely on adjusting to the care of one young child.",
        "Daily domestic schedules are focused primarily around attending to the developmental needs of her first infant.",
        "She is currently navigating everyday maternal responsibilities focused exclusively on her newborn.",
        "Her everyday parenting schedule is devoted to establishing initial routines with her single child.",
        "Daily parenting attention is concentrated on nurturing and learning the rhythms of her firstborn baby.",
    ],
    "Two": [
        "Her daily schedule requires coordinating infant care routines alongside looking after an older sibling.",
        "She manages everyday domestic responsibilities while balancing the attentional needs of two children at home.",
        "Attending to the young baby while supporting an older child shapes the pacing of her daily household routine.",
        "Daily routines involve dividing parental attention between the newborn and an older brother or sister.",
        "She balances the hands-on care of an infant with the active schedule of having two children in the home.",
    ],
    "More than two": [
        "Daily routines involve managing domestic duties while caring for multiple growing children alongside the baby.",
        "With several children in the household, her daily schedule requires continuous coordination across different age groups.",
        "She balances infant care with the bustling demands of looking after more than two children at home.",
        "Her daily schedule is structured around meeting the collective needs of multiple children in addition to the newborn.",
        "Managing the household involves coordinating care and daily routines for several young children alongside the baby.",
    ],
}

# Sentence 3: Daytime Occupation and Routine
OCCUPATION_TEMPLATES: Dict[str, List[str]] = {
    "Housewife": [
        "Her daytime hours are dedicated primarily to home management, meal preparation, and family care.",
        "Daily schedules are centered on domestic homemaking responsibilities and maintaining the household rhythm.",
        "She focuses the majority of her daytime schedule on family caregiving and everyday domestic management.",
        "Her everyday commitments revolve around home-based responsibilities and organizing domestic family life.",
        "Daytime routines are anchored in domestic homemaking duties and ongoing family maintenance.",
    ],
    "Student": [
        "She balances ongoing academic coursework and educational study schedules alongside daily postpartum routines.",
        "Academic commitments and study demands must be coordinated alongside her everyday household responsibilities.",
        "Her daily schedule involves dividing time between continuing academic pursuits and domestic infant care.",
        "She maintains academic educational goals while adapting to the everyday rhythms of family life.",
        "Coordinating coursework alongside home responsibilities forms an active component of her weekly routine.",
    ],
    "Teacher": [
        "She balances professional instructional commitments and classroom preparation with ongoing domestic life.",
        "Her daily routine incorporates professional teaching obligations alongside postpartum family adjustments.",
        "Professional educational responsibilities form a regular component of her structured weekly schedule.",
        "She coordinates instructional school duties alongside her everyday domestic and parental responsibilities.",
        "Maintaining professional teaching commitments requires ongoing coordination with her home schedule.",
    ],
    "Doctor": [
        "Her professional medical background shapes her structured daily schedule alongside domestic family life.",
        "She coordinates demanding professional clinical commitments alongside ongoing postpartum adjustments.",
        "Medical career responsibilities require careful organization alongside her daily home routines.",
        "She maintains professional clinical obligations while managing everyday domestic responsibilities.",
        "Her schedule incorporates professional healthcare commitments alongside ongoing family care.",
    ],
    "Service": [
        "She balances regular daytime workplace employment duties with ongoing domestic and family obligations.",
        "Service employment responsibilities require coordinating regular working hours alongside home life.",
        "Her daily schedule incorporates outside professional service work alongside everyday household tasks.",
        "She navigates workplace employment commitments while maintaining her daily domestic routines.",
        "Structured workplace hours form an essential part of her weekly schedule alongside family responsibilities.",
    ],
    "Business": [
        "She balances commercial business management responsibilities alongside everyday domestic routines.",
        "Managing entrepreneurial business activities occupies an active portion of her weekly daytime schedule.",
        "Commercial operations and business duties are coordinated alongside ongoing household obligations.",
        "She oversees business commitments while maintaining a steady rhythm of daily domestic activities.",
        "Entrepreneurial responsibilities require periodic coordination alongside her home care schedule.",
    ],
    "Other": [
        "Her regular schedule incorporates specialized daytime commitments alongside domestic family responsibilities.",
        "She coordinates various daytime activities outside the home with everyday postpartum routines.",
        "Specialized individual obligations outside the home are integrated into her weekly domestic schedule.",
        "Her daily routines reflect a combination of focused daytime activities and ongoing family care.",
        "She balances varied personal and occupational commitments alongside regular household duties.",
    ],
}


# =============================================================================
# THEME 2: Infant Care, Feeding Routines, and General Responsibilities
# =============================================================================

# Sentence 1: Infant Developmental Stage
INFANT_STAGE_TEMPLATES: Dict[str, List[str]] = {
    "0 to 6 months": [
        "The infant is currently under six months of age, requiring frequent and attentive physical care throughout the day.",
        "At under six months old, the young infant demands constant daytime attention and regular developmental nurturing.",
        "With the baby in the earliest infancy stage under six months, care routines are frequent and hands-on.",
        "Daily infant care centers on the continuous nurturing required by a young baby under six months of age.",
        "The baby is in the initial six months of life, following a pattern of frequent feeding and attentive soothing.",
    ],
    "6 months to 1 year": [
        "Now in the six-to-twelve-month stage, the infant is becoming increasingly active, interactive, and mobile.",
        "The child is between six and twelve months old, actively exploring surroundings and reaching initial motor milestones.",
        "Daily care corresponds to an infant between six months and one year old, requiring steady interactive engagement.",
        "At six to twelve months of age, the baby is developing noticeable physical mobility and curiosity about the home.",
        "Care routines reflect an infant between six months and one year who is actively exploring the domestic space.",
    ],
    "1 year to 1.5 year": [
        "The child is between twelve and eighteen months of age, demonstrating steady mobility and active exploration.",
        "Now in the one-to-one-and-a-half-year age window, the young toddler requires continuous physical supervision.",
        "Daily supervision reflects the energetic developmental curiosity of a child between twelve and eighteen months old.",
        "At one to 1.5 years of age, the toddler actively moves throughout the living space during waking hours.",
        "Care routines center on an active young child between twelve and eighteen months navigating toddler play.",
    ],
    "Older than 1.5 year": [
        "The child is older than eighteen months, following structured daily routines, active play, and growing independence.",
        "Being older than one and a half years, the child engages in self-directed play and predictable daily schedules.",
        "At over eighteen months of age, the active toddler participates in established daily household meal and play routines.",
        "Daily care routines center on an energetic toddler older than eighteen months who communicates regular preferences.",
        "The child is past one and a half years of age, demonstrating steady physical independence within daily home routines.",
    ],
}

# Sentence 2: Infant Feeding Practice
FEEDING_TEMPLATES: Dict[str, List[str]] = {
    "Yes": [
        "Daily infant nourishment is structured around established breastfeeding sessions scheduled across the day.",
        "She maintains a consistent maternal nursing routine as an integral component of daily infant care.",
        "Feeding routines center on regular periods of direct breastfeeding organized throughout waking hours.",
        "The child's nutritional schedule incorporates frequent and consistent maternal breastfeeding sessions.",
        "Her daily care plan includes regular nursing intervals providing steady nutrition for the infant.",
    ],
    "No": [
        "Daily infant nourishment is managed through structured alternative feeding routines rather than direct nursing.",
        "The child receives nutrition according to organized meal and feeding schedules outside of maternal breastfeeding.",
        "She provides daily nourishment through consistent alternative feeding arrangements suited to the child's age.",
        "Infant feeding is coordinated through established alternative nourishment routines throughout the day.",
        "Daily care routines incorporate planned meal schedules and alternative feeding methods for the infant.",
    ],
}

# Sentence 3: Infant Health Observation and Parental Attentiveness
HEALTH_ATTENTIVENESS_TEMPLATES: Dict[Tuple[str, str], List[str]] = {
    ("Yes", "Yes"): [
        "Recent childhood health concerns have prompted careful observation and conscientious monitoring of daily symptoms.",
        "Noted fluctuations in the infant's health have led her to maintain close, vigilant attention to physical comfort.",
        "She remains particularly mindful of the child's daily progress while managing recent minor health episodes.",
        "Episodes of childhood illness have required sustained attentiveness alongside everyday parenting care.",
        "She monitors the infant's health with deliberate care following recent observations of physical illness.",
    ],
    ("Yes", "No"): [
        "Although the child has experienced recent health concerns, everyday monitoring proceeds in a calm and steady manner.",
        "Health issues have arisen occasionally, yet daily observation and care are handled with measured composure.",
        "She addresses episodes of childhood illness systematically without substantial disruption to general routines.",
        "Recent infant health concerns are managed through practical observation and calm daily adjustments.",
        "While navigating occasional infant health challenges, she maintains an even, practical caregiving routine.",
    ],
    ("No", "Yes"): [
        "Even with the infant in general good health, she remains actively watchful regarding daily wellness and comfort.",
        "The child maintains steady physical wellness, though she continues to observe developmental milestones closely.",
        "While physical health remains uninterrupted, her everyday attention remains deeply engaged with the baby's needs.",
        "She maintains thorough daily attentiveness to the child's routine comfort despite consistent physical wellness.",
        "The infant enjoys good health, and she maintains an attentive, nurturing focus on everyday developmental habits.",
    ],
    ("No", "No"): [
        "The infant's overall health has remained steady, allowing everyday parenting routines to proceed predictably.",
        "With consistent infant wellness and no notable health disruptions, daily care routines progress smoothly.",
        "The child continues in stable health, supporting a predictable, comfortable rhythm for everyday care.",
        "Consistent childhood health provides an uninterrupted foundation for everyday infant care and feeding.",
        "Stable physical wellness in the baby fosters a steady and unhurried daily parenting rhythm.",
    ],
}


# =============================================================================
# THEME 3: Sleep Windows, Rest, and Practical Family Support
# =============================================================================

# Sentence 1: Daytime Rest and Sleep Opportunities
SLEEP_REST_TEMPLATES: Dict[Tuple[str, str], List[str]] = {
    ("Yes", "Yes"): [
        "She is able to rest during the infant's nap times and unwind comfortably when relatives assist with care.",
        "Daytime sleep windows and periods of family assistance provide dependable opportunities for personal rest.",
        "She finds opportunities to rest both when the baby is asleep and during moments when family members help out.",
        "Resting during the child's naps and stepping away while relatives attend to the baby proceed with relative ease.",
        "She takes advantage of the infant's sleep periods and family support to secure consistent personal rest.",
    ],
    ("Yes", "No"): [
        "While resting during the baby's sleep hours is difficult, she unwinds when family members take over care.",
        "She rarely naps while the infant is sleeping, though family assistance offers helpful moments to step away.",
        "Personal rest is challenging during the child's quiet hours, but family support creates intermittent breaks.",
        "She remains awake during the baby's sleep, yet finds relaxation when household members watch the child.",
        "Though sleeping during the infant's naps is infrequent, she benefits from restful breaks when others assist.",
    ],
    ("No", "Yes"): [
        "She manages to sleep while the baby is resting, though unwinding while others tend to the child feels less natural.",
        "Catching up on sleep during the infant's nap times is feasible, even if daytime family care rarely offers true relaxation.",
        "She utilizes the infant's quiet windows for personal rest, but typically remains alert when relatives assist.",
        "Personal rest is concentrated during the child's sleep periods rather than during active family caregiving hours.",
        "She secures rest while the infant is asleep, though stepping away during daytime family assistance is rare.",
    ],
    ("No", "No"): [
        "Opportunities for personal sleep and relaxation remain limited, even during quiet hours or when relatives are near.",
        "She experiences difficulty securing rest during the baby's sleep periods as well as during family-assisted care.",
        "Finding restful downtime proves challenging across both the infant's nap times and periods of household assistance.",
        "Continuous alertness often limits personal rest, whether the infant is asleep or attended by other family members.",
        "Restful breaks remain infrequent throughout the day, with limited relaxation during nap times or family care.",
    ],
}

# Sentence 2: Practical Assistance with Domestic Chores
DOMESTIC_SUPPORT_TEMPLATES: Dict[str, List[str]] = {
    "High": [
        "Household members provide substantial practical support with meal preparation, domestic cleaning, and caregiving.",
        "Extensive assistance from family members significantly lightens the daily burden of domestic chores.",
        "She receives substantial help from relatives, sharing everyday household maintenance and childcare tasks.",
        "Daily cooking, cleaning, and child-related tasks are widely supported through strong family cooperation.",
        "Family members offer generous hands-on assistance, easing the management of everyday household duties.",
    ],
    "Medium": [
        "Family members offer moderate practical assistance with daily cooking, cleaning, and household tasks.",
        "She shares a portion of domestic responsibilities with relatives while managing other tasks independently.",
        "Everyday household duties are partially supported by family, balancing shared chores and personal management.",
        "Moderate levels of domestic assistance from relatives help with select daily chores and child supervision.",
        "Household members assist with certain daily tasks, leaving other responsibilities to be managed on her own.",
    ],
    "Low": [
        "Practical assistance with domestic chores is minimal, requiring her to manage most household tasks independently.",
        "She receives limited practical help from relatives, handling the major portion of household work on her own.",
        "Daily cooking, cleaning, and infant care duties are carried out with very little external assistance.",
        "Everyday household responsibilities are largely self-managed with few contributions from other family members.",
        "Domestic duties require primarily self-directed effort, as hands-on assistance from relatives is sparse.",
    ],
}

# Sentence 3: Communication and Practical Support Needs
# Keys: (trust_value, need_category)
# trust_value in ['Yes', 'No', 'Missing']
# need_category in ['Low', 'Elevated', 'Missing']  ('Elevated' covers 'Medium' and 'High')
COMMUNICATION_NEED_TEMPLATES: Dict[Tuple[str, str], List[str]] = {
    ("Yes", "Low"): [
        "She maintains open communication with a trusted confidant, feeling that current daily support meets her needs.",
        "Having someone to speak with candidly complements her general satisfaction with available practical support.",
        "She shares daily experiences openly with a trusted relative, noting that current assistance is sufficient.",
        "A trusted confidant is available for regular conversation, and existing household support remains adequate.",
        "She readily discusses daily thoughts with someone close, expressing comfortable satisfaction with current help.",
    ],
    ("Yes", "Elevated"): [
        "She shares daily experiences with a trusted confidant while noting that extra hands-on help would be welcome.",
        "Having someone to converse with provides meaningful connection, though additional practical aid would assist her routine.",
        "She discusses personal reflections openly with someone close while recognizing that further domestic help would be useful.",
        "Open communication with a trusted individual is present alongside a helpful desire for more domestic assistance.",
        "She maintains candid discussions with a supportive confidant while expressing that more daily help would be beneficial.",
    ],
    ("Yes", "Missing"): [
        "She values having a trusted individual with whom she regularly discusses thoughts and everyday experiences.",
        "Personal reflections and daily postpartum experiences are comfortably shared with a trusted family member.",
        "She maintains an open personal dialogue with a trusted confidant as part of her regular daily routine.",
        "Having someone to speak with openly provides a supportive conversational outlet during the postpartum period.",
        "She actively shares everyday moments and personal thoughts with a dependable, trusted relative.",
    ],
    ("No", "Low"): [
        "She tends to handle personal thoughts privately while finding current levels of practical assistance adequate.",
        "Discussions about personal feelings are infrequent, yet everyday domestic support matches her routine needs.",
        "She approaches daily reflections independently, with existing household help providing an adequate foundation.",
        "While she rarely shares personal thoughts with others, available practical assistance meets her expectations.",
        "She keeps personal experiences largely to herself while managing comfortably with current household support.",
    ],
    ("No", "Elevated"): [
        "She generally handles personal thoughts privately while indicating that additional practical help would be welcome.",
        "Personal discussions are infrequent, and she expresses that extra hands-on assistance with chores would be useful.",
        "She manages her reflections independently, noting that more practical support with domestic duties would be helpful.",
        "While keeping personal experiences largely to herself, she acknowledges that extra daily assistance would be beneficial.",
        "She maintains a reserved approach to personal matters while welcoming further practical help with home tasks.",
    ],
    ("No", "Missing"): [
        "She generally keeps personal reflections private as she attends to everyday postpartum responsibilities.",
        "Daily responsibilities are managed with a reserved focus, handling personal thoughts largely on her own.",
        "She approaches everyday postpartum routines independently, keeping personal reflections to herself.",
        "Her daily schedule is maintained with self-directed focus, handling domestic adjustments privately.",
        "She navigates everyday family responsibilities quietly, managing personal thoughts with independent reserve.",
    ],
    ("Missing", "Low"): [
        "Existing household arrangements and practical support provide an adequate foundation for her daily routine.",
        "Current levels of daily assistance from family members appear sufficient for her ongoing domestic schedule.",
        "Everyday household routines proceed steadily with available domestic support matching daily requirements.",
    ],
    ("Missing", "Elevated"): [
        "She indicates that additional hands-on assistance with everyday household tasks would be beneficial to her routine.",
        "Further practical support with daily domestic chores and family duties would be a welcome addition.",
        "Extra assistance with household responsibilities would provide useful support to her daily schedule.",
    ],
    ("Missing", "Missing"): [
        "Her everyday postpartum routines continue according to established domestic household schedules.",
        "Daily home activities proceed steadily in line with ongoing family schedules and care routines.",
        "Everyday responsibilities are maintained in accordance with standard household domestic rhythms.",
    ],
}

