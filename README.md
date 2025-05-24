# 一个免费的，在超新平台上的自动刷课代码
**在运行前需要安装selenium库**  
**pip install selenium**
  
**代码位于base.py**  

<执行流程>  
<span style ="color:red">1.创建类对象</span>  
auto = AutoLesson(edge_path="你的Edge浏览器路径",username="学习通账号",password="学习通密码",course_name="课程名")  
<span style ="color:red">2.开始执行</span>  
auto.auto_execute()
