<template>
    <el-card>
        <h1>登陆</h1>
        <el-form label-width="80px" label-font-size="18px">
            <el-form-item label="密码">
                <el-input v-model="pwd" show-password/>
            </el-form-item>
            <el-form-item>
                <el-button type="primary" @click="login">确定</el-button>
            </el-form-item>
            <!-- <el-form-item label="隐藏">
                <el-switch  autocomplete="on" active-value="是" inactive-value="否"></el-switch>
            </el-form-item> -->
            <!-- <el-form-item label="路径" prop="path">
                <el-input  autocomplete="on" disabled />
            </el-form-item> -->
        </el-form>
    </el-card>
</template>

<script>
export default {
    data() {
        return {
            pwd: '',
        }
    },
    methods: {
        login(){
            console.log('pwd', this.pwd)
        }
    }
}
</script>


<style>
.el-card{
    width: 500px;
    margin: 150px auto;
}
h1{
    text-align: center;
    font-size: 20;
    padding-bottom: 60px;
}
label{
    text-align: center !important;
    font-size: 16px !important;
}

</style>