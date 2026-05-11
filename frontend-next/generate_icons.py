"""生成 PWA 图标脚本"""
import os

from PIL import Image, ImageDraw


def create_icon(size, output_path):
    """创建指定尺寸的图标"""
    # 创建蓝色背景的正方形图片
    img = Image.new('RGB', (size, size), color='#3b82f6')
    draw = ImageDraw.Draw(img)

    # 绘制白色文字 "F"
    font_size = size // 2
    # 使用默认字体
    draw.text((size * 0.25, size * 0.15), 'F', fill='white')

    # 保存为 PNG
    img.save(output_path, 'PNG')
    print(f'Created icon: {output_path} ({size}x{size})')


def main():
    # 图标尺寸列表
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]

    icons_dir = os.path.join(os.path.dirname(__file__), 'public', 'icons')
    os.makedirs(icons_dir, exist_ok=True)

    for size in sizes:
        output_path = os.path.join(icons_dir, f'icon-{size}x{size}.png')
        create_icon(size, output_path)

    print(f'\nAll icons created in {icons_dir}')


if __name__ == '__main__':
    main()
