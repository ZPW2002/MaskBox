<template>
  <div class="home">
    <!-- <h1>HideBox文件夹管理</h1> -->

    <!-- 表格区域 -->
    <div style="height:10px"/>
    <el-table 
      :data="table" 
      border 
      stripe 
      height="680" 
      :cell-style="{ textAlign: 'center' }" 
      :header-cell-style="{ textAlign: 'center' }" 
      >
      <!-- <el-row> -->
        <el-table-column prop="folder" label="文件夹" width="250"/>
        <el-table-column prop="path" label="路径"/>
      <!-- </el-row> -->
      <el-table-column prop="hide" label="隐藏" width="60"/>
      <el-table-column prop="mask" label="伪装" width="120"/>

      <el-table-column label="操作" width="210">
        <template slot="header">
          <el-row type="flex" justify="center">
            <el-col :span="10"><span class="op">操作</span></el-col>
            <el-col :span="8"><el-button size="mini" class="add" @click="addDialog" icon="el-icon-plus">添加</el-button></el-col>
          </el-row>
        </template>
        <template slot-scope="scope">
          <el-button type="info" size="mini" @click="handEdit(scope.$index, scope.row)" icon="el-icon-edit"
            round>编辑</el-button>
          <el-popconfirm title="确认删除吗？" icon="el-icon-info" icon-color="#F56C6C" @confirm="handDelete(scope.$index, scope.row)">
            <el-button type="danger" size="mini" icon="el-icon-delete" round slot="reference">删除</el-button>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑弹出窗 -->
    <el-dialog title="文件夹设置" :visible="dialogVisible" width="30%" :before-close="handleClose">
      <el-form :model="form" status-icon :rules="rules" ref="form" label-width="60px">

        <el-form-item label="文件夹" prop="folder">
          <el-input v-model="form.folder" autocomplete="on" disabled />
        </el-form-item>

        <el-form-item label="路径" prop="path">
          <el-input v-model="form.path" autocomplete="on" disabled />
        </el-form-item>

        <el-form-item label="隐藏">
          <el-switch v-model="form.hide" autocomplete="on" active-value="是" inactive-value="否"></el-switch>
        </el-form-item>

        <el-form-item label="伪装" prop="mask">
          <el-select v-model="form.mask" autocomplete="on">
            <el-option v-for="item in mask_select" :key="item.label" :label="item.label" :value="item.value"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button type="primary" @click="edit">确定</el-button>
      </span>
    </el-dialog>

    <!-- 添加弹出窗 -->
    <el-dialog title="添加文件夹" :visible="addVisible" width="30%" :before-close="addClose">
      <el-form :model="form" status-icon :rules="rules" ref="form" label-width="60px">

        <el-form-item label="文件夹" prop="folder">
          <el-row>
            <el-col :span="16"><el-input v-model="form.folder" disabled/></el-col>
            <el-col :span="8"><center><el-button @click="sel">选择</el-button></center></el-col>
          </el-row>
          
        </el-form-item>

        <el-form-item label="路径" prop="path">
          <el-input v-model="path_get" disabled/>
        </el-form-item>

        <el-form-item label="隐藏">
          <el-switch v-model="hide_get" active-value="是" inactive-value="否"></el-switch>
        </el-form-item>

        <el-form-item label="伪装" prop="mask">
          <el-select v-model="mask_get">
            <el-option v-for="item in mask_select" :key="item.label" :label="item.label" :value="item.value"></el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button type="primary" @click="add">确定</el-button>
      </span>
    </el-dialog>

  </div>
</template>

<script>
export default {
  name: 'Home',
  data() {
    return {
      table: [],
      dialogVisible: false,
      addVisible: false,
      routeDialogVisible: true,
      form: {},
      rules: {},
      path_get: null,
      mask_get: '无',
      hide_get: '否',
      mask_select: [
        {'label': '无', 'value': '无'},
        {'label': '无关联文件', 'value': '无关联文件'},
        {'label': '回收站', 'value': '回收站'},
        {'label': '脱机文件夹', 'value': '脱机文件夹'},
        {'label': '管理工具', 'value': '管理工具'},
        {'label': '历史记录', 'value': '历史记录'},
        {'label': '缓存文件夹', 'value': '缓存文件夹'},
        {'label': '拨号网络', 'value': '拨号网络'},
        {'label': '网上邻居', 'value': '网上邻居'}
      ]
    }
  },
  created() {
    this.init()
  },
  methods: {
    init() {
      this.$axios.get('/all').then(res => {
        this.table = res.data
      })
    },

    sel(){
      this.$axios.get('/sel').then(res => {
        this.path_get = res.data['path'];
        this.form.folder = res.data['folder']
        this.form.path = this.path_get;
        // this.form.mask = '无';
      })
    },

    addDialog() {
      this.addVisible = true
      this.form = {}
    },

    handEdit(index, row) {
      this.dialogVisible = true
      this.form = JSON.parse(JSON.stringify(row))
    },

    handDelete(index, row) {
      // console.log(JSON.parse(JSON.stringify(row)))
      let path = JSON.parse(JSON.stringify(row)).path
      this.$axios.post('/delete', {'path': path}).then(res => {
        if (res.code == 200) {
          this.$notify.success({
            title: '成功',
            message: res.msg,
            duration: 1000,
            position: 'bottom-right'
          })
          this.init()
        } else {
          this.$notify.success({
            title: '失败',
            message: res.msg,
            duration: 2000,
            position: 'bottom-right'
          })
        }
      })
    },

    handleClose() {
      this.dialogVisible = false
      this.init()
    },
    addClose() {
      this.addVisible = false
      this.path_get = null
      this.hide_get = '否'
      this.init()
    },

    edit() {
      this.$axios.post('/update', this.form).then(res => {
        if (res.code == 200) {
          this.handleClose()
          this.$notify.success({
            title: '成功',
            message: res.msg,
            duration: 1000,
            position: 'bottom-right'
          });
        } else {
          this.$notify.error({
            title: '错误',
            message: res.msg,
            duration: 2000,
            position: 'bottom-right'
          });
        }
      })
    },

    add() {
      if (!('path' in this.form)) {
        this.$notify.error({
          title: '错误',
          message: '未选择文件夹',
          duration: 2000,
          position: 'bottom-right'
        });
        return;
      }

      this.form.mask = this.mask_get
      this.form.hide = this.hide_get

      this.$axios.post('/add', this.form).then(res => {
        this.form={}
        this.path_get=null
        this.mask_get='无'
        this.hide_get='否'

        if (res.code == 200) {
          this.addClose()
          this.$notify.success({
            title: '成功',
            message: res.msg,
            duration: 1000,
            position: 'bottom-right'
          });
        } else {
          this.$notify.error({
            title: '错误',
            message: res.msg,
            duration: 2000,
            position: 'bottom-right'
          });
        }
      })
    }
  }
}
</script>

<style>
h1 {
  text-align: center;
  margin: 50px 0;
}

td:nth-child(-n+2){
  text-align: left !important;
}

.el-table {
  width: 95% !important;
  margin: 0 auto;
  font-family: 'consolas';
}

.el-button {
  margin: 0 5px;
}

span.op {
  display: inline-block;
  margin-left: 6px;
}

.el-dialog__body {
  padding-bottom: 0;
}


</style>
