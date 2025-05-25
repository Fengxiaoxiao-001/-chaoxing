from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import NoSuchElementException,TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class AutoLesson:
    def __init__(self,edge_path:str,username:str,password:str,course_name:str):
        """
        :param edge_path:   Edge浏览器路径
        :param username:    账号
        :param password:    密码
        :param course_name: 课程名
        """
        self.edge_options = Options()
        self.edge_options.use_chromium = True  # 启用Chromium内核模式
        self.edge_options.add_argument('--mute-audio')  # 默认静音
        self.edge_service = webdriver.EdgeService(
            exceutable_path = edge_path)
        self.username = username
        self.password = password
        self.course_name = course_name.replace(' ', '\u00a0')
        self.driver = None
        self.incomplete_tasks = True


    # ===== 登录模块（需要手动处理验证码） =====
    def _login(self):
        self.driver.get("https://passport2.chaoxing.com/login")
        try:
            self.driver.find_element(By.ID, "phone").send_keys(self.username)
        except NoSuchElementException:
            print("用户元素不存在")
        try:
            self.driver.find_element(By.ID, "pwd").send_keys(self.password)
        except NoSuchElementException:
            print("密码元素不存在")
        time.sleep(3)  # 留出时间手动处理验证码

        try:
            self.driver.find_element(By.ID, "loginBtn").click()

        except NoSuchElementException:
            print("登录元素不存在")

        time.sleep(15)

    # ===== 寻找课程模块 =====
    def _search_course(self):
        try:
            # 等待iframe加载并切换
            WebDriverWait(self.driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "frame_content"))
            )

            # 增加等待时间至20秒，要求元素可见
            course_link = WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((
                    By.XPATH,
                    f"//div[@class='course-info']//span[contains(@class,'course-name') and contains(normalize-space(.), normalize-space('{self.course_name}'))]/ancestor::a"
                ))
            )

            # 滚动到元素位置
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", course_link)

            # 跳转前确保链接有效
            target_url = course_link.get_attribute("href")
            if target_url and "http" in target_url:
                self.driver.get(target_url)
            else:
                raise ValueError("无效的链接地址")

        except TimeoutException:
            print("❌ 元素加载超时，请检查：")
            print("1. iframe嵌套 | 2. 动态加载 | 3. XPath有效性")
            # driver.save_screenshot("timeout_error.png")
        except Exception as e:
            print("❌ 发生未知错误:", str(e))

    # ===== 查询未完成点 =====
    def _query_incomplete(self):
        try:
            # Step 1: 处理诚信承诺书弹窗
            try:
                # 先等待弹窗出现（假设弹窗容器 ID 为 "commitmentPopup"）
                WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "notAgreeCommitment"))
                )

                # 再定位弹窗内的元素
                not_agree = self.driver.find_element(By.ID, "notAgreeCommitment").get_attribute("value")
                if not_agree.lower() == "true":
                    WebDriverWait(self.driver, 15).until(
                        EC.visibility_of_element_located((By.ID, "showCommitmentId"))
                    )
                    self.driver.find_element(By.CSS_SELECTOR, ".agreeButton").click()
                    self.driver.find_element(By.CSS_SELECTOR, ".agreeStart").click()
                    print("已签署诚信承诺书")
            except TimeoutException:
                print("无承诺书弹窗")

            # Step 2: 切换到章节导航菜单
            WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//li[@dataname='zj']/a"))
            ).click()

            # Step 3: 切换到章节内容iframe
            WebDriverWait(self.driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "frame_content-zj"))
            )

            # Step 4: 等待章节内容加载
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "chapter_item"))
            )


            # Step 5: 定位未完成章节
            unfinished_chapters = WebDriverWait(self.driver, 25).until(
                EC.presence_of_all_elements_located((
                    By.XPATH,
                    "//div[contains(@class,'catalog_jindu')]//span[contains(., '待完成任务点')]/ancestor::div[contains(@class, 'chapter_item')]"
                ))
            )

            print("该章节未完成" if len(unfinished_chapters) else "该章节均已完成")
            # 更新是否完成标签
            self.incomplete_tasks = True if len(unfinished_chapters) else False

            # Step 6 :执行跳转
            if unfinished_chapters:
                first_chapter = unfinished_chapters[0]
                onclick_js = first_chapter.get_attribute("onclick")

                self.driver.execute_script(onclick_js)
                print("已触发未完成任务跳转")

        except Exception as e:
            print("定位失败:", e)

    # ===== 自动播放视频 =====
    def _play_video(self):
        try:
            self.driver.switch_to.default_content()

            # 添加显式等待确保iframe存在
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
            )

            # Step1: 进入到主iframe
            main_iframe = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "iframe"))
            )
            self.driver.switch_to.frame(main_iframe)
            try:
                # Step2: 查询主iframe下的所有子iframe
                video_iframes = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "iframe[src*='video']:not([style*='display:none'])")
                    )
                )

                print(f"有{len(video_iframes)}个子iframe")

                def video_execute(subframes):
                    try:
                        # Step3: 转到子iframe并执行
                        self.driver.switch_to.frame(subframes)
                        # 触发播放
                        video = WebDriverWait(self.driver, 30).until(
                            EC.presence_of_element_located((By.ID, "video_html5_api"))
                        )

                        # 等待元数据加载（显式等待）
                        self.driver.execute_script("arguments[0].play();", video)

                        WebDriverWait(self.driver, 30).until(
                            lambda d: d.execute_script("""
                                return arguments[0].readyState >= 3 &&  // HAVE_FUTURE_DATA 或更高
                                       isFinite(arguments[0].duration) && 
                                       arguments[0].duration > 1;
                            """, video)
                        )

                        self.driver.execute_script("arguments[0].currentTime = arguments[0].duration - 1;", video)
                        self.driver.execute_script("arguments[0].playbackRate = 2;", video)
                        self.driver.execute_script("arguments[0].play();", video)

                        print("播放视频")
                        # Step4:播放状态监控
                        while True:
                            time.sleep(10)
                            if self.driver.execute_script("return arguments[0].currentTime >= arguments[0].duration - 1",
                                                     video):
                                print("播放完成")
                                break
                    finally:
                        # Step5: 退出子iframe，返回主父iframe
                        self.driver.switch_to.parent_frame()

                for subframe in video_iframes:
                    try:
                        video_execute(subframe)
                        # self._track_and_remove_listeners()
                    except Exception as e:
                        print(f"视频 {subframe.id} 播放失败: {str(e)}")
                        continue
            except TimeoutException:
                # 定义目标元素选择器
                target_div = "div#RightCon.RightCon.newTestCon"

                try:
                    # 优先在主页面查找
                    main_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, target_div))
                    )
                except TimeoutException:
                    # 主页面未找到时启动深度搜索
                    main_element = self.search_in_all_frames(self.driver, target_div)

                if main_element:
                    print("成功定位到章节测验容器")
                    input("输入回车继续运行（切记需要该章节已被完成）")
                else:
                    print("未找到目标元素，执行备用分支")
                    # 回退到默认位置
                    self.driver.switch_to.default_content()
                    # 单次滚动到底部
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    # 创建并触发点击事件
                    script = """
                    var event = new MouseEvent('click', { bubbles: true });
                    document.getElementById("prevNextFocusNext").dispatchEvent(event);
                    """
                    self.driver.execute_script(script)

            self.driver.switch_to.default_content()
            return True


        except TimeoutException as e:
            print(f"iframe加载失败: {str(e)}")
            self.driver.refresh()
            return False

        except Exception as e:
            print(f"其他异常: {str(e)}")
            self.driver.switch_to.default_content()
            return False

    # ===== 递归逻辑 =====
    def search_in_all_frames(self,driver, target_selector):
        # 尝试在当前框架查找目标元素
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, target_selector))
            )
            return element
        except TimeoutException:
            # 若未找到，递归搜索所有嵌套iframe
            return self.search_in_nested_frames(driver, target_selector)

    def search_in_nested_frames(self,driver, target_selector):
        # 获取当前层所有iframe
        iframes = driver.find_elements(By.TAG_NAME, "iframe")       # 找不到就放回一个空列表[] 不会报错

        for iframe in iframes:          # 如果为空列表[]时，跳过for循环 不会报错
            try:
                # 切换到子iframe
                driver.switch_to.frame(iframe)
                # 尝试在当前子iframe查找
                element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, target_selector))
                )
                return element
            except TimeoutException:
                # 递归深入下一层iframe
                result = self.search_in_nested_frames(driver, target_selector)
                if result: return result
            finally:
                # 返回父级iframe继续搜索
                driver.switch_to.parent_frame()
        return None

    # ===== 自动播放逻辑 =====
    def auto_execute(self):
        self.driver = webdriver.Edge(options=self.edge_options, service=self.edge_service)
        self.driver.implicitly_wait(10)
        self._login()
        self._search_course()
        while self.incomplete_tasks:
            self._query_incomplete()
            self._play_video()
            self.driver.back()
        print("该课程已经完成")
