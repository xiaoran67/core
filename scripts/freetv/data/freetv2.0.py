#!/usr/bin/env python3
"""
FreeTV 主程序 - 优化版 2.0
支持双输入配置，自动生成配置文件
"""
import urllib.request
import os
import logging
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ==================== 配置区域 - 方便修改 ====================
# 如果外部配置文件不存在，将使用以下默认配置
DEFAULT_SOURCE_URLS = [
    "https://mirror.ghproxy.com/https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u",
    "https://mirror.ghproxy.com/https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u",
]

DEFAULT_OUTPUT_FILES = {
    'complete': '直播源',
    'cctv': '央视频道', 
    'ws': '卫视频道',
    'other': '其他频道'
}

DEFAULT_DATA_FILES = {
    'rename_rules': 'data/rename_rules.txt',
    'channel_list': 'data/channel_list.txt',
    'cctv_list': 'data/cctv_list.txt',
    'ws_list': 'data/ws_list.txt'
}

DEFAULT_PROCESSING = {
    'timeout': 30,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

LOG_LEVEL = "INFO"
# ==================== 配置区域结束 ====================

# 配置日志
logging.basicConfig(level=getattr(logging, LOG_LEVEL), 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FreeTVProcessor:
    def __init__(self):
        # 设置路径
        self.script_dir = Path(__file__).parent
        self.data_dir = self.script_dir / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.output_dir = self.script_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # 加载配置
        self.config = self.load_config()
        
        # 加载数据
        self.rename_dic = self.load_rename_rules()
        self.channel_lists = self.load_channel_lists()
        
        # 存储数据
        self.freetv_lines = []
        self.categorized_channels = {
            'cctv': [],
            'ws': [], 
            'other': []
        }

    def load_config(self):
        """加载配置：优先外部配置，不存在则使用默认配置"""
        config_path = self.script_dir / "config.json"
        
        if config_path.exists():
            # 使用外部配置
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("✅ 使用外部配置文件")
                return config
            except Exception as e:
                logger.error(f"❌ 配置文件解析错误，使用默认配置: {e}")
                return self.get_default_config()
        else:
            # 使用默认配置并创建示例文件
            default_config = self.get_default_config()
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                logger.info("📝 已创建示例配置文件 config.json")
                self.create_example_data_files()
            except Exception as e:
                logger.error(f"❌ 创建配置文件失败: {e}")
            
            return default_config

    def get_default_config(self):
        """返回默认配置 - 优化版"""
        return {
            'source_urls': DEFAULT_SOURCE_URLS,
            'output_files': DEFAULT_OUTPUT_FILES,
            'data_files': DEFAULT_DATA_FILES,
            'processing': DEFAULT_PROCESSING
        }

    def create_example_data_files(self):
        """创建示例数据文件 - 使用标准CCTV命名"""
        example_data = {
            'rename_rules.txt': [
                "# 频道名称修正规则",
                "# 格式：正确名称,错误名称1,错误名称2,...",
                "CCTV1,CCTV-1,央视一套,中央一套",
                "CCTV2,CCTV-2,央视二套,中央二套",
                "CCTV3,CCTV-3,央视三套,中央三套",
                "CCTV4,CCTV-4,央视四套,中央四套",
                "CCTV5,CCTV-5,央视五套,中央五套",
                "CCTV6,CCTV-6,央视六套,中央六套",
                "CCTV7,CCTV-7,央视七套,中央七套",
                "CCTV8,CCTV-8,央视八套,中央八套",
                "CCTV9,CCTV-9,央视九套,中央九套",
                "CCTV10,CCTV-10,央视十套,中央十套",
                "CCTV11,CCTV-11,央视十一套,中央十一套",
                "CCTV12,CCTV-12,央视十二套,中央十二套",
                "CCTV13,CCTV-13,央视十三套,中央十三套",
                "CCTV14,CCTV-14,央视十四套,中央十四套",
                "CCTV15,CCTV-15,央视十五套,中央十五套",
                "CCTV16,CCTV-16,央视十六套,中央十六套",
                "CCTV17,CCTV-17,央视十七套,中央十七套",
                "湖南卫视,湖南台,HNTV",
                "浙江卫视,ZJTV,浙江台",
                "江苏卫视,JSCTV,江苏台",
                "东方卫视,DFTV,上海卫视",
                "北京卫视,BTV,北京台",
                "天津卫视,TJTV,天津台",
                "山东卫视,SDTV,山东台",
                "安徽卫视,AHTV,安徽台",
                "广东卫视,GDTV,广东台",
                "深圳卫视,SZTV,深圳台",
                "黑龙江卫视,HLJTV,黑龙江台",
                "吉林卫视,JLTV,吉林台",
                "辽宁卫视,LNTV,辽宁台",
                "四川卫视,SCTV,四川台",
                "重庆卫视,CQTV,重庆台",
                "湖北卫视,HUBTV,湖北台",
                "河南卫视,HNTV,河南台",
                "河北卫视,HEBTV,河北台",
                "江西卫视,JXTV,江西台",
                "陕西卫视,SXTV,陕西台",
                "山西卫视,SXWS,山西台",
                "广西卫视,GXTV,广西台",
                "福建卫视,FJTV,福建台",
                "云南卫视,YNTV,云南台",
                "贵州卫视,GZTV,贵州台",
                "甘肃卫视,GSCTV,甘肃台",
                "宁夏卫视,NXTV,宁夏台",
                "内蒙古卫视,NMGTV,内蒙古台",
                "新疆卫视,XJTV,新疆台",
                "西藏卫视,XZTV,西藏台",
                "海南卫视,HNTV,海南台",
                "厦门卫视,XMTV,厦门台",
                "兵团卫视,BTTV,兵团台"
            ],
            'channel_list.txt': [
                "# 总频道列表（白名单）",
                "# 只有在此列表中的频道才会被处理",
                "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5",
                "CCTV6", "CCTV7", "CCTV8", "CCTV9", "CCTV10",
                "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15",
                "CCTV16", "CCTV17",
                "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视",
                "天津卫视", "山东卫视", "安徽卫视", "广东卫视", "深圳卫视",
                "黑龙江卫视", "吉林卫视", "辽宁卫视", "四川卫视", "重庆卫视",
                "湖北卫视", "河南卫视", "河北卫视", "江西卫视", "陕西卫视",
                "山西卫视", "广西卫视", "福建卫视", "云南卫视", "贵州卫视",
                "甘肃卫视", "宁夏卫视", "内蒙古卫视", "新疆卫视", "西藏卫视",
                "海南卫视", "厦门卫视", "兵团卫视"
            ],
            'cctv_list.txt': [
                "# CCTV频道列表", 
                "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5",
                "CCTV6", "CCTV7", "CCTV8", "CCTV9", "CCTV10",
                "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15",
                "CCTV16", "CCTV17"
            ],
            'ws_list.txt': [
                "# 卫视频道列表",
                "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视",
                "天津卫视", "山东卫视", "安徽卫视", "广东卫视", "深圳卫视",
                "黑龙江卫视", "吉林卫视", "辽宁卫视", "四川卫视", "重庆卫视",
                "湖北卫视", "河南卫视", "河北卫视", "江西卫视", "陕西卫视",
                "山西卫视", "广西卫视", "福建卫视", "云南卫视", "贵州卫视",
                "甘肃卫视", "宁夏卫视", "内蒙古卫视", "新疆卫视", "西藏卫视",
                "海南卫视", "厦门卫视", "兵团卫视"
            ]
        }
        
        for filename, content in example_data.items():
            file_path = self.data_dir / filename
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(content))
                logger.info(f"📝 已创建示例文件: {filename}")

    def load_data_file(self, filename):
        """加载数据文件：优先外部文件，不存在则使用内置默认"""
        file_key = filename.replace('.txt', '')
        file_path = self.script_dir / self.config['data_files'][file_key]
        
        if file_path.exists():
            # 使用外部文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                logger.info(f"✅ 使用外部数据文件: {filename} ({len(lines)} 行)")
                return lines
            except Exception as e:
                logger.error(f"❌ 读取数据文件失败 {filename}: {e}")
                return []
        else:
            # 使用内置默认数据
            default_data = self.get_default_data().get(filename, [])
            logger.info(f"📋 使用内置默认数据: {filename} ({len(default_data)} 行)")
            return default_data

    def get_default_data(self):
        """返回内置默认数据 - 使用标准CCTV命名"""
        return {
            'rename_rules.txt': [
                "CCTV1,CCTV-1,央视一套,中央一套",
                "CCTV2,CCTV-2,央视二套,中央二套",
                "CCTV3,CCTV-3,央视三套,中央三套",
                "CCTV4,CCTV-4,央视四套,中央四套",
                "CCTV5,CCTV-5,央视五套,中央五套",
                "CCTV6,CCTV-6,央视六套,中央六套",
                "CCTV7,CCTV-7,央视七套,中央七套",
                "CCTV8,CCTV-8,央视八套,中央八套",
                "CCTV9,CCTV-9,央视九套,中央九套",
                "CCTV10,CCTV-10,央视十套,中央十套",
                "CCTV11,CCTV-11,央视十一套,中央十一套",
                "CCTV12,CCTV-12,央视十二套,中央十二套",
                "CCTV13,CCTV-13,央视十三套,中央十三套",
                "CCTV14,CCTV-14,央视十四套,中央十四套",
                "CCTV15,CCTV-15,央视十五套,中央十五套",
                "CCTV16,CCTV-16,央视十六套,中央十六套",
                "CCTV17,CCTV-17,央视十七套,中央十七套",
                "湖南卫视,湖南台,HNTV",
                "浙江卫视,ZJTV,浙江台",
                "江苏卫视,JSCTV,江苏台",
                "东方卫视,DFTV,上海卫视",
                "北京卫视,BTV,北京台",
                "天津卫视,TJTV,天津台",
                "山东卫视,SDTV,山东台",
                "安徽卫视,AHTV,安徽台",
                "广东卫视,GDTV,广东台",
                "深圳卫视,SZTV,深圳台",
                "黑龙江卫视,HLJTV,黑龙江台",
                "吉林卫视,JLTV,吉林台",
                "辽宁卫视,LNTV,辽宁台",
                "四川卫视,SCTV,四川台",
                "重庆卫视,CQTV,重庆台",
                "湖北卫视,HUBTV,湖北台",
                "河南卫视,HNTV,河南台",
                "河北卫视,HEBTV,河北台",
                "江西卫视,JXTV,江西台",
                "陕西卫视,SXTV,陕西台",
                "山西卫视,SXWS,山西台",
                "广西卫视,GXTV,广西台",
                "福建卫视,FJTV,福建台",
                "云南卫视,YNTV,云南台",
                "贵州卫视,GZTV,贵州台",
                "甘肃卫视,GSCTV,甘肃台",
                "宁夏卫视,NXTV,宁夏台",
                "内蒙古卫视,NMGTV,内蒙古台",
                "新疆卫视,XJTV,新疆台",
                "西藏卫视,XZTV,西藏台",
                "海南卫视,HNTV,海南台",
                "厦门卫视,XMTV,厦门台",
                "兵团卫视,BTTV,兵团台"
            ],
            'channel_list.txt': [
                "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5",
                "CCTV6", "CCTV7", "CCTV8", "CCTV9", "CCTV10",
                "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15",
                "CCTV16", "CCTV17",
                "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视",
                "天津卫视", "山东卫视", "安徽卫视", "广东卫视", "深圳卫视",
                "黑龙江卫视", "吉林卫视", "辽宁卫视", "四川卫视", "重庆卫视",
                "湖北卫视", "河南卫视", "河北卫视", "江西卫视", "陕西卫视",
                "山西卫视", "广西卫视", "福建卫视", "云南卫视", "贵州卫视",
                "甘肃卫视", "宁夏卫视", "内蒙古卫视", "新疆卫视", "西藏卫视",
                "海南卫视", "厦门卫视", "兵团卫视"
            ],
            'cctv_list.txt': [
                "CCTV1", "CCTV2", "CCTV3", "CCTV4", "CCTV5",
                "CCTV6", "CCTV7", "CCTV8", "CCTV9", "CCTV10",
                "CCTV11", "CCTV12", "CCTV13", "CCTV14", "CCTV15",
                "CCTV16", "CCTV17"
            ],
            'ws_list.txt': [
                "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视",
                "天津卫视", "山东卫视", "安徽卫视", "广东卫视", "深圳卫视",
                "黑龙江卫视", "吉林卫视", "辽宁卫视", "四川卫视", "重庆卫视",
                "湖北卫视", "河南卫视", "河北卫视", "江西卫视", "陕西卫视",
                "山西卫视", "广西卫视", "福建卫视", "云南卫视", "贵州卫视",
                "甘肃卫视", "宁夏卫视", "内蒙古卫视", "新疆卫视", "西藏卫视",
                "海南卫视", "厦门卫视", "兵团卫视"
            ]
        }

    def load_rename_rules(self):
        """加载重命名规则"""
        corrections = {}
        rules = self.load_data_file('rename_rules.txt')
        
        for line in rules:
            parts = line.split(',')
            if len(parts) >= 2:
                correct_name = parts[0].strip()
                for name in parts[1:]:
                    name = name.strip()
                    if name:
                        corrections[name] = correct_name
        
        logger.info(f"📝 加载了 {len(corrections)} 条重命名规则")
        return corrections

    def load_channel_lists(self):
        """加载频道列表"""
        channel_lists = {}
        for key in ['channel_list', 'cctv_list', 'ws_list']:
            channel_lists[key] = self.load_data_file(f'{key}.txt')
            logger.info(f"📺 加载 {key}: {len(channel_lists[key])} 个频道")
        
        return channel_lists

    def is_valid_channel_line(self, line):
        """检查是否为有效的频道行"""
        line = line.strip()
        return (line and 
                "#genre#" not in line and 
                "," in line and 
                "://" in line and
                not line.startswith('#'))

    def process_channel_line(self, line):
        """处理单个频道行"""
        if self.is_valid_channel_line(line):
            channel_name, channel_address = line.split(',', 1)
            # 添加频道名称作为后缀用于标识
            channel_suffix = channel_name.strip().replace(' ', '_')
            processed_line = f"{channel_name},{channel_address}${channel_suffix}"
            self.freetv_lines.append(processed_line.strip())

    def process_url(self, url):
        """处理URL"""
        try:
            logger.info(f"🌐 开始处理URL: {url}")
            req = urllib.request.Request(url)
            req.add_header('User-Agent', self.config['processing']['user_agent'])
            
            with urllib.request.urlopen(req, timeout=self.config['processing']['timeout']) as response:
                data = response.read()
                text = data.decode('utf-8')
                lines = text.splitlines()
                logger.info(f"✅ URL处理完成: {url}, 获取到 {len(lines)} 行数据")
                
                processed_count = 0
                for line in lines:
                    if self.is_valid_channel_line(line):
                        channel_name = line.split(',')[0].strip()
                        if channel_name in self.channel_lists['channel_list']:
                            self.process_channel_line(line)
                            processed_count += 1
                
                logger.info(f"📊 从 {url} 处理了 {processed_count} 个频道")
                
        except Exception as e:
            logger.error(f"❌ 处理URL时发生错误 {url}: {e}")

    def clean_url(self, url):
        """清理URL中的$后缀"""
        return url.split('$')[0]

    def rename_channel(self, data):
        """修正频道名称"""
        corrected_data = []
        for line in data:
            if ',' in line and "#genre#" not in line:
                name, url = line.split(',', 1)
                original_name = name.strip()
                if original_name in self.rename_dic:
                    corrected_name = self.rename_dic[original_name]
                    if corrected_name != original_name:
                        logger.debug(f"🔄 重命名: {original_name} -> {corrected_name}")
                    name = corrected_name
                corrected_data.append(f"{name},{url}")
            else:
                corrected_data.append(line)
        return corrected_data

    def categorize_channels(self):
        """分类频道"""
        freetv_lines_renamed = self.rename_channel(self.freetv_lines)
        
        for line in freetv_lines_renamed:
            if self.is_valid_channel_line(line):
                channel_name, channel_address = line.split(',', 1)
                clean_address = self.clean_url(channel_address.strip())
                clean_line = f"{channel_name},{clean_address}"

                # 分类逻辑
                if channel_name in self.channel_lists['cctv_list']:
                    self.categorized_channels['cctv'].append(clean_line)
                elif channel_name in self.channel_lists['ws_list']:
                    self.categorized_channels['ws'].append(clean_line)
                else:
                    self.categorized_channels['other'].append(clean_line)

    def get_beijing_time(self):
        """获取北京时间"""
        utc_time = datetime.now(timezone.utc)
        beijing_time = utc_time + timedelta(hours=8)
        return beijing_time.strftime("%Y%m%d %H:%M:%S")

    def remove_duplicates(self, channels):
        """去除重复频道（基于频道名称）"""
        seen = set()
        unique_channels = []
        for channel in channels:
            name = channel.split(',')[0] if ',' in channel else channel
            if name not in seen:
                seen.add(name)
                unique_channels.append(channel)
        return unique_channels

    def generate_output_files(self):
        """生成输出文件"""
        version = self.get_beijing_time() + ",url"
        
        # 生成完整列表
        freetv_lines_renamed = self.rename_channel(self.freetv_lines)
        unique_channels = self.remove_duplicates(freetv_lines_renamed)
        
        # 使用配置的文件名称
        output_config = self.config['output_files']
        complete_txt_name = f"{output_config['complete']}.txt"
        complete_m3u_name = f"{output_config['complete']}.m3u"
        
        output_lines = ["更新时间,#genre#", version, '', "freetv,#genre#"] + sorted(unique_channels)
        self.save_file(complete_txt_name, output_lines)
        self.generate_m3u(complete_m3u_name, unique_channels)
        
        # 生成分类列表
        self.save_categorized_files(version)

    def save_categorized_files(self, version):
        """保存分类文件"""
        output_config = self.config['output_files']
        category_mapping = {
            'cctv': 'cctv',
            'ws': 'ws', 
            'other': 'other'
        }
        
        for category, config_key in category_mapping.items():
            channels = self.categorized_channels[category]
            if channels:
                unique_channels = self.remove_duplicates(channels)
                
                # 使用配置的文件名称
                base_filename = output_config[config_key]
                txt_filename = f"{base_filename}.txt"
                m3u_filename = f"{base_filename}.m3u"
                
                output_lines = ["更新时间,#genre#", version, '', f"freetv_{config_key},#genre#"] + sorted(unique_channels)
                self.save_file(txt_filename, output_lines)
                self.generate_m3u(m3u_filename, unique_channels)
                
                logger.info(f"✅ {base_filename}: {len(unique_channels)} 个频道")

    def save_file(self, filename, content):
        """保存文本文件"""
        file_path = self.output_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            logger.info(f"💾 已保存: {filename} ({len(content)} 行)")
        except Exception as e:
            logger.error(f"❌ 保存文件错误 {filename}: {e}")

    def generate_m3u(self, filename, channels):
        """生成M3U文件"""
        file_path = self.output_dir / filename
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for line in channels:
                    if ',' in line:
                        name, url = line.split(',', 1)
                        clean_url = self.clean_url(url)
                        f.write(f"#EXTINF:-1,{name}\n")
                        f.write(f"{clean_url}\n")
            logger.info(f"💾 已保存: {filename} ({len(channels)} 个频道)")
        except Exception as e:
            logger.error(f"❌ 生成M3U文件错误 {filename}: {e}")

    def run(self):
        """主运行逻辑"""
        logger.info("🚀 开始处理FreeTV频道...")
        
        start_time = datetime.now()
        
        # 处理URL
        for url in self.config['source_urls']:
            self.process_url(url)
        
        logger.info(f"📡 获取到 {len(self.freetv_lines)} 个原始频道")
        
        if not self.freetv_lines:
            logger.error("❌ 没有获取到任何频道数据")
            return
        
        # 分类频道
        self.categorize_channels()
        
        # 统计信息
        total_categorized = sum(len(channels) for channels in self.categorized_channels.values())
        logger.info(f"📊 分类结果 - CCTV: {len(self.categorized_channels['cctv'])}, "
                   f"卫视: {len(self.categorized_channels['ws'])}, "
                   f"其他: {len(self.categorized_channels['other'])}")
        
        # 生成输出文件
        self.generate_output_files()
        
        elapsed = datetime.now() - start_time
        logger.info(f"🎉 FreeTV处理完成！耗时: {elapsed.total_seconds():.2f}秒")

def main():
    processor = FreeTVProcessor()
    processor.run()

if __name__ == "__main__":
    main()