// 常用表情映射表 (Text -> Emoji)
export const EMOTE_MAP: Record<string, string> = {
    ':smile:': '😊',
    ':laughing:': '😆',
    ':blush:': '😊',
    ':smiley:': '😃',
    ':relaxed:': '☺️',
    ':smirk:': '😏',
    ':heart_eyes:': '😍',
    ':kissing_heart:': '😘',
    ':kissing_closed_eyes:': '😚',
    ':flushed:': '😳',
    ':relieved:': '😌',
    ':satisfied:': '😆',
    ':grin:': '😁',
    ':wink:': '😉',
    ':stuck_out_tongue_winking_eye:': '😜',
    ':stuck_out_tongue_closed_eyes:': '😝',
    ':grinning:': '😀',
    ':kissing:': '😗',
    ':kissing_smiling_eyes:': '😙',
    ':stuck_out_tongue:': '😛',
    ':sleeping:': '😴',
    ':worried:': '😟',
    ':frowning:': '😦',
    ':anguished:': '😧',
    ':open_mouth:': '😮',
    ':grimacing:': '😬',
    ':confused:': '😕',
    ':hushed:': '😯',
    ':expressionless:': '😑',
    ':unamused:': '😒',
    ':sweat_smile:': '😅',
    ':sweat:': '😓',
    ':disappointed_relieved:': '😥',
    ':weary:': '😩',
    ':pensive:': '😔',
    ':disappointed:': '😞',
    ':confounded:': '😖',
    ':fearful:': '😨',
    ':cold_sweat:': '😰',
    ':persevere:': '😣',
    ':cry:': '😢',
    ':sob:': '😭',
    ':joy:': '😂',
    ':astonished:': '😲',
    ':scream:': '😱',
    ':tired_face:': '😫',
    ':angry:': '😠',
    ':rage:': '😡',
    ':triumph:': '😤',
    ':sleepy:': '😪',
    ':yum:': '😋',
    ':mask:': '😷',
    ':sunglasses:': '😎',
    ':dizzy_face:': '😵',
    ':imp:': '👿',
    ':smiling_imp:': '😈',
    ':neutral_face:': '😐',
    ':no_mouth:': '😶',
    ':innocent:': '😇',
    ':alien:': '👽',
    ':yellow_heart:': '💛',
    ':blue_heart:': '💙',
    ':purple_heart:': '💜',
    ':heart:': '❤️',
    ':green_heart:': '💚',
    ':broken_heart:': '💔',
    ':heartbeat:': '💓',
    ':heartpulse:': '💗',
    ':two_hearts:': '💕',
    ':revolving_hearts:': '💞',
    ':cupid:': '💘',
    ':sparkling_heart:': '💖',
    ':thumbsup:': '👍',
    ':thumbsdown:': '👎',
    ':clap:': '👏',
    ':pray:': '🙏',
    ':ok_hand:': '👌',
    ':muscle:': '💪',
    ':facepunch:': '👊',
    ':v:': '✌️',
    ':wave:': '👋',
    ':hand:': '✋',
    ':raised_hands:': '🙌',
    ':point_up:': '☝️',
    ':point_down:': '👇',
    ':point_left:': '👈',
    ':point_right:': '👉',
    ':trophy:': '🏆',
    ':star:': '⭐',
    ':star2:': '🌟',
    ':sunflower:': '🌻',
    ':champagne:': '🍾',
    ':balloon:': '🎈',
    ':tada:': '🎉',
    ':confetti_ball:': '🎊',
    ':fire:': '🔥',
    ':100:': '💯',
};

/**
 * 将文本中的表情代码替换为 Emoji
 * @param text - 原始文本
 * @returns 替换后的文本
 */
export function parseEmotes(text: string): string {
    if (!text) return '';

    let result = text;
    for (const [code, emoji] of Object.entries(EMOTE_MAP)) {
        // 使用全局替换
        result = result.split(code).join(emoji);
    }
    return result;
}

/**
 * 获取所有可用的表情列表
 */
export function getAvailableEmotes() {
    return Object.entries(EMOTE_MAP).map(([code, emoji]) => ({
        code,
        emoji,
        category: getCategory(code),
    }));
}

/**
 * 简单的表情分类
 */
function getCategory(code: string): string {
    if (code.includes('heart')) return '情感';
    if (code.includes('hand') || code.includes('thumbs') || code.includes('clap') || code.includes('pray') || code.includes('muscle') || code.includes('punch') || code.includes('point') || code.includes('wave')) return '手势';
    if (code.includes('smile') || code.includes('laugh') || code.includes('grin') || code.includes('wink') || code.includes('kiss') || code.includes('tongue') || code.includes('joy') || code.includes('cry') || code.includes('angry') || code.includes('rage') || code.includes('fear') || code.includes('worried') || code.includes('confused') || code.includes('sleep') || code.includes('mask') || code.includes('sunglasses') || code.includes('devil') || code.includes('alien') || code.includes('imp')) return '表情';
    if (code.includes('trophy') || code.includes('star') || code.includes('fire') || code.includes('100') || code.includes('tada') || code.includes('balloon')) return '庆祝';
    return '其他';
}
