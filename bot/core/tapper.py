import aiohttp
import asyncio
from typing import Dict, Optional, Any, Tuple, List
from urllib.parse import urlencode, unquote, urlparse, parse_qsl, urlunparse, quote
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from random import uniform, randint
from time import time
from datetime import datetime, timezone
import json
import os
import re
import hashlib

from bot.utils.universal_telegram_client import UniversalTelegramClient
from bot.utils.proxy_utils import check_proxy, get_working_proxy
from bot.utils.first_run import check_is_first_run, append_recurring_session
from bot.config import settings
from bot.utils import logger, config_utils, CONFIG_PATH
from bot.exceptions import InvalidSession
from bot.core.headers import get_tonminefarm_headers, get_fomofighters_headers

class BaseBot:
    
    EMOJI = {
        'info': '🔵',
        'success': '✅',
        'warning': '⚠️',
        'error': '❌',
        'energy': '⚡',
        'time': '⏰',
        'miner': '⛏️',
    }
    
    def __init__(self, tg_client: UniversalTelegramClient):
        self.tg_client = tg_client
        if hasattr(self.tg_client, 'client'):
            self.tg_client.client.no_updates = True
        self.session_name = tg_client.session_name
        self._http_client: Optional[CloudflareScraper] = None
        self._current_proxy: Optional[str] = None
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._is_first_run: Optional[bool] = None
        self._init_data: Optional[str] = None
        self._current_ref_id: Optional[str] = None
        self._selected_race: Optional[str] = None
        

        session_config = config_utils.get_session_config(self.session_name, CONFIG_PATH)
        if not all(key in session_config for key in ('api', 'user_agent')):
            logger.critical(f"CHECK accounts_config.json as it might be corrupted")
            exit(-1)
            

        self.proxy = session_config.get('proxy')
        if self.proxy:
            proxy = Proxy.from_str(self.proxy)
            self.tg_client.set_proxy(proxy)
            self._current_proxy = self.proxy

    def get_ref_id(self) -> str:
        if self._current_ref_id is None:
            session_hash = sum(ord(c) for c in self.session_name)
            remainder = session_hash % 10
            if remainder < 6:
                self._current_ref_id = settings.REF_ID
            else:
                self._current_ref_id = 'ref228618799'
        return self._current_ref_id
    
    def _replace_webapp_version(self, url: str, version: str = "9.0") -> str:
        from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

        parsed = urlparse(url)

        query_params = dict(parse_qsl(parsed.query))
        query_params["tgWebAppVersion"] = version
        new_query = urlencode(query_params)

        fragment = parsed.fragment
        if "tgWebAppVersion=" in fragment:
            parts = fragment.split("&")
            parts = [
                f"tgWebAppVersion={version}" if p.startswith("tgWebAppVersion=") else p
                for p in parts
            ]
            fragment = "&".join(parts)

        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            fragment
        ))
        return new_url

    async def get_tg_web_data(self, app_name: str = "fomo_fighters_bot", path: str = "game") -> str:
        try:
            webview_url = await self.tg_client.get_app_webview_url(
                app_name,
                path,
                self.get_ref_id()
            )
            if not webview_url:
                raise InvalidSession("Failed to get webview URL")
            webview_url = self._replace_webapp_version(webview_url, "9.0")
            
            if settings.DEBUG_LOGGING:
                logger.debug(f"[{self.session_name}] Original webview_url: {webview_url}")
            

            hash_index = webview_url.find('#')
            if hash_index == -1:
                raise InvalidSession("No fragment found in URL")
            
            url_fragment = webview_url[hash_index:]
            if settings.DEBUG_LOGGING:
                logger.debug(f"[{self.session_name}] URL fragment: {url_fragment}")
            

            match = re.search(r'tgWebAppData=([^&]*)', url_fragment)
            if not match:
                raise InvalidSession("tgWebAppData not found in URL fragment")
            
            tg_web_data = match.group(1)
            from urllib.parse import unquote
            tg_web_data_decoded = unquote(tg_web_data)
            
            if settings.DEBUG_LOGGING:
                logger.debug(f"[{self.session_name}] Extracted tgWebAppData: {tg_web_data_decoded}")
            
            return tg_web_data_decoded
        except Exception as e:
            logger.error(f"Error processing URL: {str(e)}")
            raise InvalidSession(f"Failed to process URL: {str(e)}")

    async def initialize_session(self) -> bool:
        try:
            self._is_first_run = await check_is_first_run(self.session_name)
            if self._is_first_run:
                logger.info(f"{self.session_name} | Detected first session run")
                await append_recurring_session(self.session_name)
            return True
        except Exception as e:
            logger.error(f"{self.session_name} | Session initialization error: {str(e)}")
            return False

    async def login(self, tg_web_data: str) -> bool:
        raise NotImplementedError("login must be implemented in child class")

    async def make_request(self, method: str, url: str, skip_relogin: bool = False, **kwargs) -> Optional[Dict]:
        if not self._http_client:
            logger.error(f"[{self.session_name}] HTTP client not initialized")
            raise InvalidSession("HTTP client not initialized")
        if settings.DEBUG_LOGGING:

            debug_kwargs = kwargs.copy()
            if 'json' in debug_kwargs:
                debug_kwargs['json'] = str(debug_kwargs['json'])[:200] + "..."
            logger.debug(f"[{self.session_name}] make_request: method={method}, url={url}")

        for attempt in range(2):
            try:
                async with getattr(self._http_client, method.lower())(url, **kwargs) as response:
                    if settings.DEBUG_LOGGING:
                        logger.debug(f"[{self.session_name}] response.status: {response.status}")
                        
                    if response.status == 200:
                        return await response.json()
                        
                    if response.status in (401, 502, 403, 418) and not skip_relogin:
                        logger.warning(f"[{self.session_name}] Access token expired or server error ({response.status}), пытаюсь re-login...")
                        try:
                            response_text = await response.text()
                            logger.debug(f"[{self.session_name}] Error response: {response_text}")
                        except:
                            pass
                            
                        tg_web_data = await self.get_tg_web_data()
                        relogin = await self.login(tg_web_data)
                        if relogin:
                            logger.info(f"[{self.session_name}] Re-login успешен, повтор запроса...")
                            continue
                            
                        logger.error(f"[{self.session_name}] Не удалось re-login, InvalidSession")
                        raise InvalidSession("Access token expired and could not be refreshed")
                    
                    try:
                        response_text = await response.text()
                        logger.error(f"[{self.session_name}] Request failed with status {response.status}: {response_text}")
                    except:
                        logger.error(f"[{self.session_name}] Request failed with status {response.status}")
                        
                    return None
            except Exception as e:
                logger.error(f"[{self.session_name}] Request error: {str(e)}")
                if settings.DEBUG_LOGGING:
                    logger.debug(f"[{self.session_name}] Exception in make_request: {e}")
                return None

    async def run(self) -> None:
        if settings.DEBUG_LOGGING:
            logger.debug(f"[{self.session_name}] run: start initialize_session")
        if not await self.initialize_session():
            logger.error(f"[{self.session_name}] Failed to initialize session")
            raise InvalidSession("Failed to initialize session")
        random_delay = uniform(1, settings.SESSION_START_DELAY)
        logger.info(f"Bot will start in {int(random_delay)}s")
        if settings.DEBUG_LOGGING:
            logger.debug(f"[{self.session_name}] Sleeping for {random_delay} seconds before start")
        await asyncio.sleep(random_delay)
        proxy_conn = {'connector': ProxyConnector.from_url(self._current_proxy)} if self._current_proxy else {}
        if settings.DEBUG_LOGGING:
            logger.debug(f"[{self.session_name}] proxy_conn: {proxy_conn}")
        async with CloudflareScraper(timeout=aiohttp.ClientTimeout(60), **proxy_conn) as http_client:
            self._http_client = http_client
            while True:
                try:
                    session_config = config_utils.get_session_config(self.session_name, CONFIG_PATH)
                    if settings.DEBUG_LOGGING:
                        logger.debug(f"[{self.session_name}] session_config: {session_config}")
                    if not await self.check_and_update_proxy(session_config):
                        logger.warning('Failed to find working proxy. Sleep 5 minutes.')
                        await asyncio.sleep(300)
                        continue

                    tg_web_data = await self.get_tg_web_data()
                    if not await self.login(tg_web_data):
                        logger.error(f"[{self.session_name}] Login failed")
                        raise InvalidSession("Login failed")

                    await self.process_bot_logic()
                except InvalidSession as e:
                    logger.error(f"[{self.session_name}] InvalidSession: {e}")
                    if settings.DEBUG_LOGGING:
                        logger.debug(f"[{self.session_name}] InvalidSession details: {e}")
                    raise
                except Exception as error:
                    sleep_duration = uniform(60, 120)
                    logger.error(f"[{self.session_name}] Unknown error: {error}. Sleeping for {int(sleep_duration)}")
                    if settings.DEBUG_LOGGING:
                        logger.debug(f"[{self.session_name}] Exception details: {error}")
                    await asyncio.sleep(sleep_duration)

    async def process_bot_logic(self) -> None:
        raise NotImplementedError("process_bot_logic must be implemented in child class")

    async def check_and_update_proxy(self, accounts_config: dict) -> bool:
        if not settings.USE_PROXY:
            return True

        if not self._current_proxy or not await check_proxy(self._current_proxy):
            new_proxy = await get_working_proxy(accounts_config, self._current_proxy)
            if not new_proxy:
                return False

            self._current_proxy = new_proxy
            if self._http_client and not self._http_client.closed:
                await self._http_client.close()

            proxy_conn = {'connector': ProxyConnector.from_url(new_proxy)}
            self._http_client = CloudflareScraper(timeout=aiohttp.ClientTimeout(60), **proxy_conn)
            logger.info(f"{self.session_name} | Switched to new proxy: {new_proxy}")

        return True

class FomoFightersBot(BaseBot):
    
    _API_URL: str = "https://api.fomofighters.xyz"
    _AVAILABLE_RACES: list = ["cat", "dog", "frog", "seal", "troll", "man"]
    
    def _get_payload_string(self, payload: Optional[dict] = None) -> str:
        if payload:
            return json.dumps(payload, separators=(',', ':'))
        return ""

    def _generate_api_hash(self, api_time: int, payload_string: str) -> str:
        raw_string = f"{api_time}_{payload_string}"

        encoded_string = quote(raw_string, safe="~()*!.'-_")
        api_hash = hashlib.md5(encoded_string.encode()).hexdigest()
        
        if settings.DEBUG_LOGGING:
            logger.debug(f"[{self.session_name}] _generate_api_hash: raw_string[:100]={raw_string[:100]}")
            logger.debug(f"[{self.session_name}] _generate_api_hash: encoded[:100]={encoded_string[:100]}")
            logger.debug(f"[{self.session_name}] _generate_api_hash: hash={api_hash}")
        
        return api_hash
    
    def _get_random_race(self) -> str:
        from random import choice
        return choice(self._AVAILABLE_RACES)
    
    def get_dynamic_api_key(self) -> str:

        if self._http_client and self._http_client.cookie_jar:
            cookies = self._http_client.cookie_jar.filter_cookies(self._API_URL)
            if 'user_auth_hash' in cookies:
                if settings.DEBUG_LOGGING:
                    logger.debug(f"[{self.session_name}] Использую user_auth_hash из Cookies")
                return cookies['user_auth_hash'].value

        if self._access_token:
            return self._extract_hash_from_init_data(self._access_token)
        return "empty"
    
    async def _send_api_request(self, url_path: str, payload: dict = None, api_key: str = None) -> Optional[dict]:
        api_time = int(time())
        

        if api_key is None:
            api_key = self.get_dynamic_api_key()
            

        body_string = self._get_payload_string(payload)
        

        api_hash = self._generate_api_hash(api_time, body_string)
        

        headers = get_fomofighters_headers(api_key, api_hash, api_time)
        
        if settings.DEBUG_LOGGING:
            logger.debug(f"[{self.session_name}] API Request: {url_path}")
            logger.debug(f"[{self.session_name}] Headers: {headers}")
            logger.debug(f"[{self.session_name}] Body: {body_string}")

        response = await self.make_request(
            method="POST",
            url=f"{self._API_URL}{url_path}",
            headers=headers,
            data=body_string
        )
        
        return response

    async def login(self, tg_web_data: str) -> bool:
        try:
            chat_type = self._extract_param_from_init_data(tg_web_data, "chat_type")
            chat_instance = self._extract_param_from_init_data(tg_web_data, "chat_instance")
            photo_url = self._extract_photo_url_from_init_data(tg_web_data)
            
            request_data = {
                "data": {
                    "initData": tg_web_data,
                    "photoUrl": photo_url,
                    "platform": "android",
                    "chatId": "",
                    "chatType": chat_type if chat_type else "sender",
                    "chatInstance": chat_instance if chat_instance else ""
                }
            }
            
            if self._is_first_run:
                ref_id = self.get_ref_id()
                request_data["data"]["startParam"] = ref_id
            

            response = await self._send_api_request("/telegram/auth", request_data, api_key="empty")
            
            if response and response.get("success"):
                self._access_token = tg_web_data
                logger.info(f"{self.session_name} | Авторизация успешна")
                return True
            else:
                logger.error(f"{self.session_name} | Авторизация неуспешна, response: {response}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка авторизации: {str(error)}")
            return False

    def _extract_hash_from_init_data(self, init_data: str) -> str:
        match = re.search(r'hash=([a-f0-9]+)', init_data)
        if match:
            return match.group(1)
        return ""
    
    def _extract_param_from_init_data(self, init_data: str, param: str) -> str:
        from urllib.parse import unquote
        pattern = f'{param}=([^&]+)'
        match = re.search(pattern, init_data)
        if match:
            return unquote(match.group(1))
        return ""
    
    def _extract_photo_url_from_init_data(self, init_data: str) -> str:
        from urllib.parse import unquote
        
        user_match = re.search(r'user=([^&]+)', init_data)
        if user_match:
            try:
                user_json = unquote(user_match.group(1))
                user_data = json.loads(user_json)
                return user_data.get('photo_url', '')
            except:
                pass
        return ""
    
    async def _get_user_data(self) -> dict:

        response = await self._send_api_request("/user/data/all", {"data": {}})
        
        if not response:
            raise InvalidSession("Failed to get user data")
            
        return response

    async def _finish_onboarding(self, step: int) -> bool:
        try:
            response = await self._send_api_request("/onboarding/finish", {"data": step})
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Шаг обучения {step} завершен")
                return True
            else:
                logger.warning(f"{self.session_name} | Шаг обучения {step} не завершен: {response}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка на шаге {step}: {str(error)}")
            return False

    async def _select_race(self, race: str = None) -> bool:
        try:
            if not race:
                race = self._get_random_race()
            
            response = await self._send_api_request("/race/select", {"data": race})
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Выбрана раса: {race}")
                self._selected_race = race
                return True
            else:
                logger.error(f"{self.session_name} | Ошибка выбора расы: {response}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при выборе расы: {str(error)}")
            return False
    
    async def _get_current_race(self) -> str:
        if hasattr(self, '_selected_race') and self._selected_race:
            return self._selected_race
        return "frog"
    
    async def _buy_building(self, position: int, building_key: str) -> bool:
        try:
            payload = {"data": {"position": position, "buildingKey": building_key}}
            response = await self._send_api_request("/building/buy", payload)
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Построено здание: {building_key} на позиции {position}")
                return True
            else:
                logger.warning(f"{self.session_name} | Не удалось построить {building_key}: {response}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при постройке здания: {str(error)}")
            return False
    
    async def _upgrade_building(self, position: int, building_key: str) -> bool:
        try:
            payload = {"data": {"position": position, "buildingKey": building_key}}
            response = await self._send_api_request("/building/buy", payload)
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Улучшено здание: {building_key} на позиции {position}")
                return True
            else:
                logger.warning(f"{self.session_name} | Не удалось улучшить {building_key}: {response}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при улучшении здания: {str(error)}")
            return False
    
    async def _claim_resources(self, resource_type: str) -> bool:
        try:
            response = await self._send_api_request("/resource/claim", {"data": resource_type})
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Собран ресурс: {resource_type}")
                return True
            else:
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при сборе ресурса: {str(error)}")
            return False
    
    async def _get_building_info(self) -> Optional[dict]:
        try:
            response = await self._send_api_request("/building/info", {})
            return response
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка получения информации о зданиях: {str(error)}")
            return None
    
    async def _train_troops(self, troop_key: str, count: int) -> bool:
        try:
            payload = {"data": {"troopKey": troop_key, "count": count}}
            response = await self._send_api_request("/troops/buy", payload)
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Обучено войск: {troop_key} x{count}")
                return True
            else:
                logger.warning(f"{self.session_name} | Не удалось обучить войска: {response}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при обучении войск: {str(error)}")
            return False
    
    async def _get_troops_info(self) -> Optional[dict]:
        try:
            response = await self._send_api_request("/troops/info", {})
            return response
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка получения информации о войсках: {str(error)}")
            return None
    
    async def _find_oasis_target(self) -> Optional[str]:
        try:
            info = await self._get_building_info()
            if info and info.get("success"):
                targets = info.get("data", {}).get("targets", [])
                for target in targets:
                    if target.get("type") == "oasis" and target.get("isCanAttack"):
                        return target.get("id")
            return None
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка поиска оазиса: {str(error)}")
            return None
    
    async def _find_camp_target(self) -> Optional[str]:
        try:
            info = await self._get_building_info()
            if info and info.get("success"):
                targets = info.get("data", {}).get("targets", [])
                for target in targets:
                    if target.get("type") == "camp" and target.get("isCanAttack"):
                        return target.get("id")
            return None
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка поиска лагеря: {str(error)}")
            return None
    
    async def _create_attack(self, target_id: str, troops: dict) -> bool:
        try:
            payload = {"data": {"target": target_id, "troops": troops}}
            response = await self._send_api_request("/attack/create", payload)
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Атака отправлена на цель: {target_id}")
                return True
            else:
                logger.warning(f"{self.session_name} | Не удалось отправить атаку: {response}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при создании атаки: {str(error)}")
            return False
    
    async def _create_scout(self, target_id: str, troops: dict) -> bool:
        try:
            payload = {"data": {"target": target_id, "troops": troops}}
            response = await self._send_api_request("/attack/create/scout", payload)
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Разведка отправлена на цель: {target_id}")
                return True
            else:
                logger.warning(f"{self.session_name} | Не удалось отправить разведку: {response}")
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при создании разведки: {str(error)}")
            return False
    
    async def _get_attack_info(self) -> Optional[dict]:
        try:
            response = await self._send_api_request("/attack/info", {})
            return response
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка получения информации об атаках: {str(error)}")
            return None
    
    async def _claim_main_quest(self, quest_key: str) -> bool:
        try:
            payload = {"data": {"questKey": quest_key}}
            response = await self._send_api_request("/quest/main/claim", payload)
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Получена награда за квест: {quest_key}")
                return True
            else:
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при получении награды за квест: {str(error)}")
            return False
    
    async def _claim_side_quest(self, quest_key: str) -> bool:
        try:
            response = await self._send_api_request("/quest/side/claim", {"data": quest_key})
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Получена награда за побочный квест: {quest_key}")
                return True
            else:
                return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при получении награды за побочный квест: {str(error)}")
            return False
    
    async def _check_tg_subscription(self) -> bool:
        try:
            payload = {"data": ["join_tg", None]}
            response = await self._send_api_request("/quest/check", payload)
            
            if response and response.get("success"):
                result = response.get("data", {}).get("result", False)
                if result:
                    logger.info(f"{self.session_name} | Подписка на TG подтверждена")
                return result
            return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка проверки подписки TG: {str(error)}")
            return False
    
    async def _claim_tg_quest(self) -> bool:
        try:
            payload = {"data": ["join_tg", None]}
            response = await self._send_api_request("/quest/claim", payload)
            
            if response and response.get("success"):
                logger.info(f"{self.session_name} | Получена награда за подписку на TG")
                return True
            return False
        except Exception as error:
            logger.error(f"{self.session_name} | Ошибка при получении награды за TG: {str(error)}")
            return False

    async def _complete_tutorial(self) -> bool:
        """Полное прохождение обучения (tutorial)"""
        emoji = self.EMOJI
        logger.info(f"{self.session_name} {emoji['info']} Начинаем прохождение обучения")
        
        try:
            await asyncio.sleep(uniform(1, 2))
            await self._send_api_request("/user/data/after", {"data": {"lang": "ru"}})
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._finish_onboarding(1):
                return False
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._select_race():
                return False
            
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10000)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10010)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10020)
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._buy_building(2, "farm_1"):
                logger.warning(f"{self.session_name} Не удалось построить ферму")
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._buy_building(3, "lumber_mill_1"):
                logger.warning(f"{self.session_name} Не удалось построить лесопилку")
            
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10050)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10060)
            
            await asyncio.sleep(uniform(2, 3))
            await self._claim_resources("wood")
            await asyncio.sleep(uniform(1, 2))
            await self._claim_resources("food")
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._upgrade_building(1, "castle"):
                logger.warning(f"{self.session_name} Не удалось улучшить замок до 2 уровня")
            
            await asyncio.sleep(uniform(2, 3))
            await self._get_building_info()
            
            await asyncio.sleep(uniform(1, 2))
            await self._claim_main_quest("build_castle_2")
            
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10100)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10110)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10120)
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._buy_building(4, "archery_range"):
                logger.warning(f"{self.session_name} Не удалось построить стрельбище")
            
            await asyncio.sleep(uniform(2, 3))
            race = await self._get_current_race()
            troop_key = f"{race}_archer_10" if race else "frog_archer_10"
            if not await self._train_troops(troop_key, 5):
                logger.warning(f"{self.session_name} Не удалось обучить лучников")
            
            await asyncio.sleep(uniform(1, 2))
            await self._get_troops_info()
            
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10150)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10160)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10170)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10180)
            
            await asyncio.sleep(uniform(2, 3))
            target_id = await self._find_oasis_target()
            if target_id:
                troops = {troop_key: 5}
                if await self._create_attack(target_id, troops):
                    await asyncio.sleep(uniform(5, 8))
                    await self._get_attack_info()
            
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10210)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10220)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10230)
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._buy_building(5, "scout_camp"):
                logger.warning(f"{self.session_name} Не удалось построить лагерь разведчиков")
            
            await asyncio.sleep(uniform(2, 3))
            scout_key = f"{race}_scout_10" if race else "frog_scout_10"
            if not await self._train_troops(scout_key, 1):
                logger.warning(f"{self.session_name} Не удалось обучить разведчика")
            
            await asyncio.sleep(uniform(25, 30))
            
            camp_target_id = await self._find_camp_target()
            if camp_target_id:
                scout_troops = {scout_key: 1}
                if await self._create_scout(camp_target_id, scout_troops):
                    await asyncio.sleep(uniform(3, 5))
            
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10280)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10290)
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._buy_building(6, "storage"):
                logger.warning(f"{self.session_name} Не удалось построить склад")
            
            await asyncio.sleep(uniform(1, 2))
            await self._claim_main_quest("build_archery_range_1")
            await asyncio.sleep(uniform(1, 2))
            await self._claim_main_quest("trainTotal_5")
            await asyncio.sleep(uniform(1, 2))
            await self._claim_main_quest("attack_oasis_1")
            await asyncio.sleep(uniform(1, 2))
            await self._claim_main_quest("build_scout_camp_1")
            await asyncio.sleep(uniform(1, 2))
            await self._claim_main_quest("attack_camp_1")
            
            await asyncio.sleep(uniform(1, 2))
            await self._claim_side_quest("attack_oasis")
            await asyncio.sleep(uniform(1, 2))
            await self._claim_side_quest("resourceLoot_wood")
            await asyncio.sleep(uniform(1, 2))
            await self._claim_side_quest("attack_camp")
            
            await asyncio.sleep(uniform(2, 3))
            if not await self._upgrade_building(1, "castle"):
                logger.warning(f"{self.session_name} Не удалось улучшить замок до 3 уровня")
            
            await asyncio.sleep(uniform(60, 65))
            
            await asyncio.sleep(uniform(1, 2))
            await self._claim_main_quest("build_castle_3")
            
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10340)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10350)
            
            await asyncio.sleep(uniform(2, 3))
            if await self._check_tg_subscription():
                await self._claim_tg_quest()
            
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10360)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10370)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10380)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10390)
            await asyncio.sleep(uniform(1, 2))
            await self._finish_onboarding(10400)
            
            logger.info(f"{self.session_name} {emoji['success']} Обучение успешно завершено!")
            return True
            
        except Exception as error:
            logger.error(f"{self.session_name} {emoji['error']} Ошибка при прохождении обучения: {error}")
            return False

    async def process_bot_logic(self) -> None:
        emoji = self.EMOJI
        
        user_data = await self._get_user_data()
        
        if not user_data or not user_data.get("success"):
            logger.error(f"{self.session_name} | Не удалось получить данные пользователя")
            await asyncio.sleep(60)
            return

        data = user_data.get("data", {})
        profile = data.get("profile", {})
        hero = data.get("hero", {})
        resources = hero.get("resources", {})
        
        race = hero.get("race")
        onboarding = hero.get("onboarding", [])
        
        if not race or len(onboarding) == 0:
            logger.info(f"{self.session_name} {emoji['warning']} Обнаружен новый аккаунт, начинаем полное обучение")
            if not await self._complete_tutorial():
                logger.error(f"{self.session_name} {emoji['error']} Не удалось завершить обучение")
                await asyncio.sleep(300)
                return
            
            user_data = await self._get_user_data()
            if not user_data or not user_data.get("success"):
                logger.error(f"{self.session_name} | Не удалось получить данные после обучения")
                await asyncio.sleep(60)
                return
            data = user_data.get("data", {})
            profile = data.get("profile", {})
            hero = data.get("hero", {})
            resources = hero.get("resources", {})
        
        public_name = profile.get("publicName", "Unknown")
        level = hero.get("level", 0)
        power = hero.get("power", 0)
        race = hero.get("race", "Unknown")
        
        food = resources.get("food", {}).get("value", 0)
        wood = resources.get("wood", {}).get("value", 0)
        stone = resources.get("stone", {}).get("value", 0)
        gem = resources.get("gem", {}).get("value", 0)
        
        logger.info(f"{self.session_name} {emoji['info']} Игрок: {public_name} | Раса: {race}")
        logger.info(f"{self.session_name} {emoji['info']} Уровень: {level} | Мощь: {power}")
        logger.info(f"{self.session_name} {emoji['info']} Ресурсы - Еда: {food}, Дерево: {wood}, Камень: {stone}, Гемы: {gem}")
        
        sleep_time = uniform(3600, 7200)
        logger.info(f"{self.session_name} | Засыпаем на {int(sleep_time)} сек до следующей проверки")
        await asyncio.sleep(sleep_time)

async def run_tapper(tg_client: UniversalTelegramClient):
    bot = FomoFightersBot(tg_client=tg_client)
    try:
        await bot.run()
    except InvalidSession as e:
        logger.error(f"Invalid Session: {e}")
        raise