# -*- coding: utf-8 -*-
##############################################################################
#
#    Swiss Postfinance File Delivery Services module for Odoo
#    Copyright (C) 2014-2016 Compassion CH
#    @author: Nicolas Tran, Emanuel Cino
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, exceptions
import logging
import base64
import tempfile
import shutil
import pysftp
import os

_logger = logging.getLogger(__name__)


class PaymenOrderUploadSepaWizard(models.TransientModel):
    """ Allows to upload the generated SEPA electronic payment
        file for Switzerland to FDS Postfinance.
    """
    _name = 'payment.order.upload.sepa.wizard'
    _description = 'Upload SEPA to FDS'

    fds_account_id = fields.Many2one(
        'fds.postfinance.account', 'FDS Account',
        default=lambda self: self._get_default_account()
    )
    fds_directory_id = fields.Many2one(
        'fds.postfinance.directory', 'FDS Directory',
        help='Select one upload directory. Be sure to have at least one '
             'directory configured with upload access rights.'
    )
    attachment_id = fields.Many2one(
        'ir.attachment', required=True, ondelete='cascade'
    )
    file_data = fields.Binary(
        'Generated File', related='attachment_id.datas', readonly=True
    )
    filename = fields.Char(
        related='attachment_id.name', readonly=True
    )
    payment_order_id = fields.Many2one(
        'account.payment.order', 'Payment Order', required=True, readonly=True,
        ondelete='cascade'
    )
    state = fields.Selection([
        ('upload', 'upload'),
        ('finish', 'finish')], readonly=True, default='upload'
    )

    ##################################
    #         Button action          #
    ##################################
    @api.multi
    def upload_generate_file_button(self):
        ''' upload pain_001 file to the FDS Postfinance by sftp

            :returns action: configuration for the next wizard's view
            :raises Warning:
                - If no fds account and directory selected
                - if current user do not have key
                - if unable to connect to sftp
        '''
        self.ensure_one()
        (key, key_pass) = self._get_sftp_key()

        try:
            # create tmp file
            tmp_d = tempfile.mkdtemp()
            tmp_key = self._create_tmp_file(key.private_key_crypted, tmp_d)[0]
            tmp_f = self._create_tmp_file(self.attachment_id.datas, tmp_d)[0]
            old_path_f = os.path.join(tmp_d, tmp_f.name)
            new_path_f = os.path.join(tmp_d, ''.join(self.filename.split(':')))
            shutil.move(old_path_f, new_path_f)

            # upload to sftp
            with pysftp.Connection(
                    self.fds_account_id.hostname,
                    username=self.fds_account_id.username,
                    private_key=tmp_key.name,
                    private_key_pass=key_pass) as sftp:

                with sftp.cd(self.fds_directory_id.name):
                    sftp.put(new_path_f)
                    self.state = 'finish'
                    self.env.cr.commit()
                    _logger.info("[OK] upload file (%s) ", self.filename)

            # change to initial name file (mandatory because of the close)
            shutil.move(new_path_f, old_path_f)
            self._add2historical()
        except Exception as e:
            _logger.error("Unable to connect to the sftp: %s", e)
            raise exceptions.Warning('Unable to connect to the sftp')

        finally:
            try:
                tmp_key.close()
            except:
                _logger.error("remove tmp_key file failed")
            try:
                tmp_f.close()
            except:
                _logger.error("remove tmp_f file failed")
            try:
                shutil.rmtree(tmp_d)
            except:
                _logger.error("remove tmp directory failed")

        self.payment_order_id.generated2uploaded()
        return True

    ##############################
    #          function          #
    ##############################
    def _get_default_account(self):
        """ Select one account if only one exists. """
        fds_accounts = self.env['fds.postfinance.account'].search([])
        if len(fds_accounts) == 1:
            return fds_accounts.id
        else:
            return False

    @api.onchange('fds_account_id')
    def _get_default_upload_directory(self):
        self.ensure_one()
        if self.fds_account_id:
            default_directory = self.fds_account_id.directory_ids.filtered(
                lambda d: d.name == 'pain-001-in' and
                d.allow_upload_file)
            if len(default_directory) == 1:
                self.fds_directory_id = default_directory

    @api.multi
    def _get_sftp_key(self):
        ''' private function that get the SFTP key needed for connection
            with the server.

            :returns (str key, str key_pass):
            :riases Warning: if no key found
        '''
        fds_authentication_key_obj = self.env['fds.authentication.keys']
        key = fds_authentication_key_obj.search([
            ['user_id', '=', self.env.user.id],
            ['fds_account_id', '=', self.fds_account_id.id]])

        if not key:
            raise exceptions.Warning('You don\'t have key')

        if not key.key_active:
            raise exceptions.Warning('Key not active')

        key_pass = fds_authentication_key_obj.config()
        return (key, key_pass)

    @api.multi
    def _create_tmp_file(self, data, tmp_directory=None):
        ''' private function that write data to a tmp file and if no tmp
            directory use, create one.

            :param str data: data in base64 format
            :param str tmp_directory: path of the directory
            :returns (obj file, str directory): obj of type tempfile
        '''
        self.ensure_one()
        try:
            if not tmp_directory:
                tmp_directory = tempfile.mkdtemp()

            tmp_file = tempfile.NamedTemporaryFile(dir=tmp_directory)
            tmp_file.write(base64.b64decode(data))
            tmp_file.flush()
            return (tmp_file, tmp_directory)
        except Exception as e:
            _logger.error("Bad handling tmp in fds_inherit_sepa_wizard: %s", e)

    @api.multi
    def _add2historical(self):
        ''' private function that add the upload file to historic

            :returns: None
        '''
        self.ensure_one()
        values = {
            'payment_order_id': self.payment_order_id.id,
            'fds_account_id': self.fds_account_id.id,
            'filename': self.filename,
            'directory_id': self.fds_directory_id.id,
            'state': 'uploaded'}
        historical_dd_obj = self.env['fds.sepa.upload.history']
        historical_dd_obj.create(values)