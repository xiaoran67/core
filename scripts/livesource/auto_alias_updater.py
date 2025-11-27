# auto_alias_updater.py
"""
自动化频道别名更新系统
支持从订阅源文件读取URL列表，自动拉取直播源并生成频道别名纠正文件
输出路径: scripts/livesource/corrections_name.txt
"""

import requests
import re
import os
import time
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import hashlib

# 默认订阅源URL列表（如果订阅源文件不存在时使用）
DEFAULT_SUBSCRIPTION_URLS = [
    "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/Collection/LiveSource2025.txt",
    "https://raw.githubusercontent.com/xiaoran67/update/refs/heads/main/output/Collection/LiveSource2026.txt",
    "https://raw.githubusercontent.com/develop202/migu_video/refs/heads/main/interface.txt",
    "https://raw.githubusercontent.com/kakaxi-1/IPTV/refs/heads/main/iptv.txt",
    "https://freetv.fun/test_channels_original_new.txt",
]

# 默认订阅源文件名
SUBSCRIPTION_FILE = "subscription_sources.txt"
# 输出文件路径
OUTPUT_FILE = "scripts/livesource/corrections_name.txt"

class LiveSourceFetcher:
    """直播源拉取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.timeout = 30
        self.max_retries = 2
    
    def fetch_live_sources(self, source_urls: List[str]) -> Dict[str, str]:
        """从多个URL拉取直播源内容"""
        all_content = {}
        
        for url in source_urls:
            for attempt in range(self.max_retries):
                try:
                    print(f"📡 正在拉取 ({attempt+1}/{self.max_retries}): {url}")
                    response = self.session.get(url, timeout=self.timeout)
                    response.encoding = 'utf-8'
                    
                    if response.status_code == 200:
                        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                        all_content[f"source_{url_hash}"] = response.text
                        print(f"✅ 成功拉取: {url}")
                        break
                    else:
                        print(f"❌ 拉取失败 {url}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ 拉取错误 {url}: {e}")
                    if attempt == self.max_retries - 1:
                        print(f"❌ 放弃拉取: {url}")
                
                time.sleep(1)
        
        return all_content

class AdvancedChannelParser:
    """高级频道解析器"""
    
    def __init__(self):
        self.clean_patterns = [
            r'\[.*?\]', r'\(.*?\)', r'【.*?】', r'#EXTINF.*?,',
            r'group-title=".*?"', r'tvg-name=".*?"', r'tvg-id=".*?"',
            r'tvg-logo=".*?"'
        ]
        
        self.quality_indicators = [
            '4K', '1080P', '720P', 'HD', '超清', '高清', '标清', '蓝光', 'FHD'
        ]

    def parse_channels_from_content(self, content: str) -> List[str]:
        """从内容中解析出频道名称列表"""
        channels = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            channel_name = self.extract_channel_name(line)
            if channel_name and len(channel_name) > 1:
                channels.append(channel_name)
        
        return list(set(channels))

    def extract_channel_name(self, line: str) -> str:
        """从单行内容提取频道名称"""
        # M3U格式: #EXTINF:-1,频道名称
        if line.startswith('#EXTINF'):
            match = re.search(r'#EXTINF:.*?,(.+)', line)
            if match:
                return self.clean_channel_name(match.group(1))
        
        # TXT格式: 频道名称,URL
        if ',' in line and ('http://' in line or 'https://' in line):
            parts = line.split(',', 1)
            if len(parts) >= 2:
                return self.clean_channel_name(parts[0])
        
        return self.clean_channel_name(line)

    def clean_channel_name(self, name: str) -> str:
        """清洗频道名称"""
        if not name:
            return ""
        
        cleaned = name
        for pattern in self.clean_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        cleaned = re.sub(r'https?://[^\s]+', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'^[,\s]+|[,\s]+$', '', cleaned)
        
        return cleaned

class ChannelAliasManager:
    """频道别名管理器"""
    
    def __init__(self):
        self.standard_to_aliases: Dict[str, Set[str]] = defaultdict(set)
        self.alias_to_standard: Dict[str, str] = {}

    def find_standard_name(self, channel_name: str) -> Tuple[str, bool]:
        """查找频道对应的标准名称"""
        if channel_name in self.alias_to_standard:
            return self.alias_to_standard[channel_name], False
        
        clean_name = self.clean_for_matching(channel_name)
        for alias, standard in self.alias_to_standard.items():
            if self.clean_for_matching(alias) == clean_name:
                return standard, False
        
        standard_name = self.generate_standard_name(channel_name)
        return standard_name, True

    def clean_for_matching(self, name: str) -> str:
        """为匹配清理名称"""
        name = name.lower()
        for quality in ['4k', '1080p', '720p', 'hd', '超清', '高清', '标清']:
            name = name.replace(quality, '')
        name = re.sub(r'[^\w]', '', name)
        return name

    def generate_standard_name(self, channel_name: str) -> str:
        """生成标准频道名称"""
        # CCTV频道
        cctv_match = re.search(r'CCTV[\-\s]*(\d+\+?)', channel_name, re.IGNORECASE)
        if cctv_match:
            num = cctv_match.group(1)
            return f"CCTV{num.upper()}"
        
        # 卫视频道
        for region in ['湖南', '江苏', '浙江', '北京', '东方', '广东', '深圳', '天津']:
            if region in channel_name and '卫视' in channel_name:
                return f"{region}卫视"
        
        # 其他频道
        clean_name = self.clean_channel_name(channel_name)
        return clean_name[:30] if clean_name else "Unknown"

    def clean_channel_name(self, name: str) -> str:
        """基础频道名称清洗"""
        for quality in ['4K', '1080P', '720P', 'HD', '超清', '高清', '标清']:
            name = name.replace(quality, '')
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    def add_channel(self, channel_name: str):
        """添加频道到别名系统"""
        if not channel_name or len(channel_name) < 2:
            return
            
        standard_name, is_new = self.find_standard_name(channel_name)
        
        if is_new:
            print(f"🆕 发现新频道: {channel_name} -> {standard_name}")
            base_aliases = self.generate_base_aliases(standard_name)
            self.standard_to_aliases[standard_name].update(base_aliases)
            
            for alias in base_aliases:
                self.alias_to_standard[alias] = standard_name
        
        if channel_name != standard_name:
            self.standard_to_aliases[standard_name].add(channel_name)
            self.alias_to_standard[channel_name] = standard_name

    def generate_base_aliases(self, standard_name: str) -> List[str]:
        """为基础频道名称生成基础别名"""
        aliases = []
        
        if standard_name.startswith('CCTV'):
            num = standard_name[4:]
            aliases.extend([
                f"CCTV-{num}", f"CCTV {num}", f"CCTV{num.zfill(2)}",
                standard_name.lower(), f"cctv-{num.lower()}", f"cctv {num.lower()}"
            ])
            
            cctv_types = {
                '1': ['综合'], '2': ['财经'], '3': ['综艺'], 
                '4': ['国际', '中文国际'], '5': ['体育'], '5+': ['体育', '体育赛事'],
                '6': ['电影'], '7': ['国防军事', '军农'], '8': ['电视剧'],
                '9': ['纪录', '纪录片'], '10': ['科教'], '11': ['戏曲']
            }
            
            if num in cctv_types:
                for ctype in cctv_types[num]:
                    aliases.extend([
                        f"{standard_name}{ctype}", f"CCTV-{num}{ctype}", f"CCTV {num} {ctype}"
                    ])
        
        elif standard_name.endswith('卫视'):
            base = standard_name[:-2]
            aliases.extend([f"{base}电视台", f"{base}台", standard_name.lower()])
        
        return aliases

    def save_aliases_to_file(self, output_path: str):
        """保存别名到指定文件"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        cctv_channels = {}
        satellite_channels = {}
        other_channels = {}
        
        for standard, aliases in self.standard_to_aliases.items():
            unique_aliases = sorted([a for a in set(aliases) if a and a != standard])
            
            if standard.startswith('CCTV'):
                cctv_channels[standard] = unique_aliases
            elif '卫视' in standard:
                satellite_channels[standard] = unique_aliases
            else:
                other_channels[standard] = unique_aliases
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 这是频道名称的别名名单，用于获取接口时将多种名称映射为一个名称的结果，可以提升获取量与准确率\n")
            f.write("# 格式：模板频道名称,别名1,别名2,别名3\n")
            f.write("# This is the alias list for channel names, used to map multiple names to a single name when fetching from the interface, improving the fetch volume and accuracy.\n")
            f.write("# Format: TemplateChannelName,Alias1,Alias2,Alias3\n\n")
            
            if cctv_channels:
                f.write("# 央视频道\n")
                for standard in sorted(cctv_channels.keys()):
                    aliases_str = ','.join(cctv_channels[standard])
                    f.write(f"{standard},{aliases_str}\n")
                f.write("\n")
            
            if satellite_channels:
                f.write("# 卫视频道\n")
                for standard in sorted(satellite_channels.keys()):
                    aliases_str = ','.join(satellite_channels[standard])
                    f.write(f"{standard},{aliases_str}\n")
                f.write("\n")
            
            if other_channels:
                f.write("# 其他频道\n")
                for standard in sorted(other_channels.keys()):
                    aliases_str = ','.join(other_channels[standard])
                    f.write(f"{standard},{aliases_str}\n")
        
        print(f"💾 别名文件已保存: {output_path}")

class AutoAliasUpdater:
    """自动别名更新器"""
    
    def __init__(self):
        self.fetcher = LiveSourceFetcher()
        self.parser = AdvancedChannelParser()
        self.manager = ChannelAliasManager()

    def load_subscription_sources(self, subscription_file: str) -> List[str]:
        """从订阅源文件加载URL列表"""
        urls = []
        
        try:
            if os.path.exists(subscription_file):
                print(f"📋 从文件加载订阅源: {subscription_file}")
                with open(subscription_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and (
                            line.startswith('http://') or line.startswith('https://')
                        ):
                            urls.append(line)
            else:
                print(f"📋 订阅源文件不存在，使用默认订阅源")
                urls = DEFAULT_SUBSCRIPTION_URLS
            
            print(f"📋 加载了 {len(urls)} 个订阅源")
            return urls
            
        except Exception as e:
            print(f"❌ 加载订阅源文件失败: {e}")
            print(f"📋 使用默认订阅源")
            return DEFAULT_SUBSCRIPTION_URLS

    def update_aliases(self, subscription_file: str, output_file: str) -> bool:
        """更新频道别名系统"""
        print("🚀 开始更新频道别名系统...")
        
        source_urls = self.load_subscription_sources(subscription_file)
        if not source_urls:
            print("❌ 没有找到有效的订阅源URL")
            return False

        contents = self.fetcher.fetch_live_sources(source_urls)
        if not contents:
            print("❌ 未能成功拉取任何直播源内容")
            return False

        total_channels = 0
        successful_sources = 0
        
        for source_name, content in contents.items():
            if content.strip():
                successful_sources += 1
                channels = self.parser.parse_channels_from_content(content)
                print(f"📺 {source_name}: 解析到 {len(channels)} 个频道")
                total_channels += len(channels)
                
                for channel in channels:
                    self.manager.add_channel(channel)

        current_count = len(self.manager.standard_to_aliases)
        
        print(f"\n📊 === 更新统计 ===")
        print(f"✅ 成功拉取源: {successful_sources}/{len(source_urls)}")
        print(f"📺 处理频道总数: {total_channels}")
        print(f"🏷️ 标准频道数量: {current_count}")
        
        if current_count > 0:
            self.manager.save_aliases_to_file(output_file)
            return True
        else:
            print("❌ 未能生成任何频道别名")
            return False

def main():
    """主函数"""
    updater = AutoAliasUpdater()
    success = updater.update_aliases(SUBSCRIPTION_FILE, OUTPUT_FILE)
    
    # 设置退出代码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()